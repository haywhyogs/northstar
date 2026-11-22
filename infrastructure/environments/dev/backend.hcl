# Where this environment keeps its Terraform state (created by infrastructure/bootstrap). Not secrets.
# Use: terraform init -backend-config=backend.hcl
resource_group_name  = "rg-northstar-tfstate"
storage_account_name = "stnorthstartfyk0wi8"
container_name       = "tfstate"
key                  = "dev.tfstate"
use_azuread_auth     = true
