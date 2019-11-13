# def multiple_tries(func, times, exceptions):
#     for _ in range(times):
#         try:
#             return func()
#         except Exception as e:
#             if not isinstance(e, exceptions):
#                 raise # reraises unexpected exceptions
#     raise ValueError("Something") # reraises if attempts are unsuccessful


# Builds the DataDog tags from the instaclustr data
def buildTags(node, ic_cluster_id):
    id = node["id"] or ''
    public_ip = node["publicIp"] or ''
    private_ip = node["privateIp"] or ''
    rack_name = node["rack"]["name"] or ''
    data_centre_custom_name = node["rack"]["dataCentre"]["customDCName"] or ''
    data_centre_name = node["rack"]["dataCentre"]["name"] or ''
    data_centre_provider = node["rack"]["dataCentre"]["provider"] or ''
    provider_account_name = node["rack"]["providerAccount"]["name"] or ''
    provider_account_provider = node["rack"]["providerAccount"]["provider"] or ''

    tag_list = ['ic_node_id:' + id,
                'ic_cluster_id:' + ic_cluster_id,
                'ic_public_ip:' + public_ip,
                'ic_private_ip:' + private_ip,
                'ic_rack_name:' + rack_name,
                'ic_data_centre_custom_name:' + data_centre_custom_name,
                'ic_data_centre_name:' + data_centre_name,
                'ic_data_centre_provider:' + data_centre_provider,
                'ic_provider_account_name:' + provider_account_name,
                'ic_provider_account_provider:' + provider_account_provider
                ]
    if data_centre_provider == 'AWS_VPC':
        tag_list = tag_list + [
            'region:' + node["rack"]["dataCentre"]["name"].lower().replace("_", "-"),
            'availability_zone:' + node["rack"]["name"]
        ]
    return tag_list
