# Akamai Configuration Cloner (Pulumi + Python)

This project provides a robust workflow for cloning existing Akamai Property configurations into a brand-new setup, targeting the **Staging** network. It is specifically designed to handle **Shared Certificate (Standard TLS)** hostnames and **Switchkey** account contexts.

## 🔎 Resource Discovery
Before running Pulumi, you must identify your Source and Destination IDs. Since group creation is generally a provisioned service (not self-service API), you must find existing groups.

### 1. Find your Group and Contract IDs
Use the Akamai CLI to browse your account hierarchy:

```bash
# List all groups and their parent/contract associations
akamai property groups list
```

### 2. Find IDs for an Existing Property
If you know the property name but not its location:

```bash
# This returns the contractId and groupId for the specific property
akamai property search --property-name "MY_EXISTING_CONFIG"
```

## 🚀 Quick Start

### 1. Prerequisites
* **Pulumi CLI** installed.
* **Python 3.9+** and **pip** installed.
* **Akamai API Credentials**: An `.edgerc` file with Property Manager (PAPI) read/write permissions.

### 2. Environment Setup
```bash
# Clone the repository
git clone <your-repo-url>
cd akamai-migration

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install pulumi pulumi-akamai
```

### 3. Identity Configuration (Switchkey)
> **Note:** If you are NOT using a Switchkey account, skip to **Step 4**.

If you are using a Switchkey account, you must set the provider context globally:

```bash
# Specify the .edgerc section
pulumi config set akamai:configSection "default"

# Specify the Account Switchkey ID
pulumi config set akamai:accountKey "F-AC-XXXXXX"
```

### 4. Property Configuration
Define the source you are cloning from and the destination you are creating.

```bash
# Source settings (What you are copying)
pulumi config set sourcePropertyName "EXISTING_CONFIG_NAME"

# Destination settings (The new clone)
pulumi config set contractId "ctr_XXXX"
pulumi config set groupId "grp_XXXX"
pulumi config set newPropertyName "CLONED_STAGING_CONFIG"
pulumi config set newPropertyHostname "staging-video.example.com"
pulumi config set newEdgeHostname "example.com.akamaized.net"
pulumi config set notificationEmail "admin@example.com"
```

---

## ⚠️ Important "Gotchas" & Lessons Learned

### 1. The Rule Format (Schema) Trap
* **Issue:** If your source configuration is old (e.g., created in 2018), cloning its rules into a modern property often results in a `400 Bad Request` regarding `json-schema-invalid`. This occurs because behaviors like `breadcrumbs` exist in the rules but aren't recognized by ancient schema versions.
* **Solution:** Hardcode a modern, stable `rule_format` (e.g., `v2026-02-16`) in your `akamai.Property` resource. This forces the API to validate the old rules against a modern, feature-rich dictionary.

### 2. Edge Hostname Validation
* **Issue:** You cannot simply assign a string to a property's `cname_to` field. If the Edge Hostname does not exist as an object in Akamai, the Property creation will fail with a `bad-cnameto` error.
* **Solution:** Always define an `akamai.EdgeHostName` resource in your script and pass its `.edge_hostname` output to the Property resource. This ensures the "handshake" between the hostname and the configuration exists.

### 3. Pulumi Plain Values vs. Outputs
* **Issue:** Using `akamai.get_property_rules(...)` returns a **plain string**. Trying to use `.apply()` on it will throw an `AttributeError: 'str' object has no attribute 'apply'`.
* **Solution:** * Use `get_property_rules` for immediate, synchronous data (standard Python strings).
    * Use `get_property_rules_output` if you need to chain the result to other asynchronous resources.

### 4. Version Selection
* **Issue:** Properties often have many versions. Pulling the `latest_version` might clone a broken draft.
* **Solution:** Explicitly target the environment you want to copy:
    * Use `source_prop_metadata.production_version` for the live site.
    * Use `source_prop_metadata.staging_version` for the latest tested changes.

### 5. Standard TLS (Shared Cert) Constraints
* **Issue:** Shared Cert activations fail if the security settings are mismatched.
* **Solution:** * **Hostname Level:** `cert_provisioning_type` must be `CPS_MANAGED`.
    * **Rule Level:** The rule options must have `is_secure: False`. The script automatically patches this during the clone.

### 6. Formal Product Names
* **Issue:** Shorthand IDs like `prd_AMD` can cause inconsistent API behavior.
* **Solution:** Always use the formal product ID: `prd_Adaptive_Media_Delivery`.

---

## 🛠 Usage
Once configured, run the following to preview and deploy:

```bash
# See what will be created
pulumi preview

# Deploy to Akamai Staging
pulumi up
```

## 🧹 Cleanup
To delete the cloned property and its associated edge hostname:

```bash
pulumi destroy
```

---
*Developed as a Infrastructure-as-Code (IaC) template for Akamai Adaptive Media Delivery (AMD).*
