# Runbook: recover a lost or corrupted Terraform state file

**Symptom:** `terraform plan` suddenly wants to **create everything** (or destroy things nobody changed), although the
resources still exist in Azure. The state blob was deleted, overwritten or corrupted.

**Never `apply` in this situation:** Terraform has forgotten what it manages and would try to create duplicates.

State lives in the bootstrap storage account (ADR-0008), with **blob versioning** and **7-day soft delete**:
every write keeps the previous version, and deleted blobs can be recovered.

## 1. Stop changes
Tell the team (and pause the pipeline) so nobody applies while state is wrong.

## 2. Find a good version
```bash
SA=<state storage account>     # terraform output in infrastructure/bootstrap
KEY=dev.tfstate                # the environment's state file

az storage blob list --account-name "$SA" -c tfstate --prefix "$KEY" --include v --auth-mode login \
  --query "[].{version:versionId, current:isCurrentVersion, modified:properties.lastModified, size:properties.contentLength}" -o table
```
Pick the most recent version from **before** the incident, at the size the state normally has (tens of KB).
Ignore 0-byte versions (the deletion) and ~181-byte versions: those are **empty** states that Terraform wrote when it
ran after the file was gone. Each plan or apply also adds versions, because acquiring and releasing the lock writes the blob.

## 3. Restore it as the current state
```bash
VERSION=<versionId from step 2>
az storage blob download --account-name "$SA" -c tfstate -n "$KEY" --version-id "$VERSION" \
  -f restored.tfstate --auth-mode login
az storage blob upload --account-name "$SA" -c tfstate -n "$KEY" -f restored.tfstate --overwrite --auth-mode login
rm restored.tfstate            # state can contain sensitive values: don't leave copies around
```

## 4. Verify
```bash
terraform plan                 # expected: "No changes. Your infrastructure matches the configuration."
```
If the restored version is slightly old, the plan may show a few real differences: review them before applying anything.

## If no good version exists
Re-attach each resource to a fresh state with `terraform import` (or `import` blocks), resource by resource, until
`terraform plan` shows no changes.

## Prevention
- Versioning and soft delete stay enabled on the state account; account keys stay disabled.
- Only the platform team and the CI/CD identity hold `Storage Blob Data Contributor` on it.
- State is never edited by hand; use `terraform state` commands when a change is needed.
