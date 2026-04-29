import pulumi
import pulumi_akamai as akamai
import json

config = pulumi.Config()

# --- 1. SETTINGS & IDENTITY ---
# Ensure these are set via: pulumi config set ...
contract_id      = config.require("contractId")
group_id         = config.require("groupId")
product_id       = "prd_Adaptive_Media_Delivery"
source_prop_name = config.require("sourcePropertyName")
new_prop_name    = config.require("newPropertyName")
new_prop_host    = config.require("newPropertyHostname")
new_edge_host    = config.require("newEdgeHostname")
email            = config.require("notificationEmail")

# This is the "Fix" for the 2018 schema issue. 
# It allows 'breadcrumbs' to be validated correctly.
STABLE_RULE_FORMAT = "v2026-02-16" 

# --- 2. FETCH SOURCE (The "Template") ---
# We look up the source configuration without managing it.
source_prop_metadata = akamai.get_property(name=source_prop_name)

# We pull the rules from the live PRODUCTION version to be safe.
# Fallback logic: Use Staging if it exists, otherwise use Latest
target_version = source_prop_metadata.staging_version or source_prop_metadata.latest_version

source_rules = akamai.get_property_rules(
    property_id=source_prop_metadata.id,
    contract_id=contract_id,
    group_id=group_id,
    version=target_version
)

# --- 3. CREATE NEW INFRASTRUCTURE ---

# A. Create the Edge Hostname from scratch
edge_hostname_res = akamai.EdgeHostName("sharedCertEdgeHostname",
    product_id=product_id,
    contract_id=contract_id,
    group_id=group_id,
    edge_hostname=new_edge_host,
    ip_behavior="IPV6_COMPLIANCE"
)

# B. Rule Patching: Ensures the JSON structure is valid for the new property
def patch_rules_for_clone(rules_json_str):
    rules_dict = json.loads(rules_json_str)
    # MANDATORY: Shared Cert / Standard TLS requires is_secure: False
    rules_dict["rules"]["options"] = {"is_secure": False}
    return json.dumps(rules_dict)

# C. Create the New Property (The actual "Clone" step)
new_property = akamai.Property("clonedProperty",
    name=new_prop_name,
    contract_id=contract_id,
    group_id=group_id,
    product_id=product_id,
    rule_format=STABLE_RULE_FORMAT, 
    hostnames=[akamai.PropertyHostnameArgs(
        cname_from=new_prop_host,
        cname_to=edge_hostname_res.edge_hostname, 
        cert_provisioning_type="CPS_MANAGED",
    )],
    rules=patch_rules_for_clone(source_rules.rules)
)

# --- 4. DEPLOY TO STAGING ---
staging_activation = akamai.PropertyActivation("activateStaging",
    property_id=new_property.id,
    version=new_property.latest_version,
    network="STAGING",
    contacts=email,
    note=f"Clean clone from {source_prop_name} (Prod v{source_prop_metadata.production_version})",
    auto_acknowledge_rule_warnings=True 
)

# --- 5. EXPORTS ---
pulumi.export("new_property_id", new_property.id)
pulumi.export("edge_hostname", edge_hostname_res.edge_hostname)
pulumi.export("activation_status", staging_activation.status)
