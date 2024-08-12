# openfoam-cloud

### Install Google Cloud SDK

1. install and init gloud sdk
2. set default login credentials gcloud auth application-default login https://cloud.google.com/docs/authentication/provide-credentials-adc?hl=de#how-to

```shell
gcloud auth application-default login
```

3. login to ggloud terminal 

```shell 
gcloud auth login --no-launch-browser
```

1. clone repo

   ```shell
   git clone 
   ```

2. Create the virtual environment

   ```shell
   python -m venv venv
   ```

3. Activate Environment

   ```shell
   source venv/bin/activate
   ```

4. Install dependencies

   ```shell
   pip install -e .
   ```

   needs  pip ≥ 21.3


### Troubleshooting

if import storage error: 
```python
pip install --upgrade google-cloud-storage
```

### Useful Links

- https://cloud.google.com/ (Console)
- https://cloud.google.com/sdk/docs/install?hl=de  (SDK/CLI)
- https://console.cloud.google.com/batch/jobs?organizationId=638990494627&project=icp-gcp-405410 (Batch)
- https://console.cloud.google.com/storage/browser/openfoam-default-bucket?organizationId=638990494627&project=icp-gcp-405410&pageState=(%22StorageObjectListTable%22:(%22f%22:%22%255B%255D%22))&prefix=&forceOnObjectsSortingFiltering=false (Bucket)
- https://console.cloud.google.com/logs/ (Logs)
- https://console.cloud.google.com/billing/016CE0-90683A-E53850/budgets?authuser=1&hl=de&organizationId=638990494627 (Billing/Budget)
