# Alerts for dev (Day 6). Azure Monitor checks a log query on a schedule and emails the on-call person when it matches.
# Starts here in the environment; it moves into a module once a second team (fx-rates) needs the same alerts.

# Who gets told. One action group per environment; every alert sends to it.
resource "azurerm_monitor_action_group" "oncall" {
  name                = "ag-${local.name}-oncall"
  resource_group_name = azurerm_resource_group.this.name
  short_name          = "ns-dev" # max 12 characters, shown in SMS/email headers
  tags                = local.tags

  email_receiver {
    name                    = "platform-oncall"
    email_address           = var.alert_email # set in terraform.tfvars (gitignored), never in Git
    use_common_alert_schema = true
  }
}

# "The payments worker is down": no Running worker pod in payments-dev in the last 10 minutes.
# While the worker is down, payments stay Pending (the outbox keeps them safe), so a person must know.
resource "azurerm_monitor_scheduled_query_rules_alert_v2" "payments_worker_down" {
  name                = "alert-payments-dev-worker-down"
  display_name        = "payments-dev: worker is down"
  description         = "No Running payments-worker pod in payments-dev. Payments will stay Pending until it's back. Runbook: docs/runbooks."
  resource_group_name = azurerm_resource_group.this.name
  location            = local.location
  scopes              = [module.monitoring.log_analytics_workspace_id]
  severity            = 1 # 0 = critical ... 4 = verbose. Customer payments are delayed, so high.

  evaluation_frequency = "PT5M"  # run the query every 5 minutes
  window_duration      = "PT10M" # look at the last 10 minutes (Container insights reports every 5)

  criteria {
    # summarize with no "by" always returns one row, even when no worker rows exist at all (scaled to 0 or deleted).
    query                   = <<-KQL
      KubePodInventory
      | where Namespace == "payments-dev" and Name startswith "payments-worker"
      | summarize running = countif(PodStatus == "Running")
      | where running == 0
    KQL
    time_aggregation_method = "Count" # count the rows the query returns
    operator                = "GreaterThan"
    threshold               = 0 # any row = the worker is down

    failing_periods {
      minimum_failing_periods_to_trigger_alert = 1
      number_of_evaluation_periods             = 1
    }
  }

  auto_mitigation_enabled = true # the alert resolves itself (and emails "Resolved") when the worker is back

  action {
    action_groups = [azurerm_monitor_action_group.oncall.id]
  }

  tags = local.tags
}
