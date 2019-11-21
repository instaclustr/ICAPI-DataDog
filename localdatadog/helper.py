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
    ic_cluster_id = 'ic_cluster_id:' + ic_cluster_id
    ic_node_id = 'ic_node_id:' + node.get('id') if node.get('id') else ''
    ic_public_ip = 'ic_public_ip:' + node.get('publicIp') if node.get('publicIp') else ''
    ic_private_ip = 'ic_private_ip:' + node.get('privateIp') if node.get('privateIp') else ''
    ic_rack_name, ic_data_centre_custom_name, ic_data_centre_name,\
        ic_data_centre_provider, ic_provider_account_name,\
        ic_provider_account_provider = '', '', '', '', '', ''
    if node.get('rack'):
        ic_rack_name = 'ic_rack_name:' + node["rack"]["name"] or ''
        ic_data_centre_custom_name = 'ic_data_centre_custom_name:' + node["rack"]["dataCentre"]["customDCName"] or ''
        ic_data_centre_name = 'ic_data_centre_name:' + node["rack"]["dataCentre"]["name"] or ''
        ic_data_centre_provider = 'ic_data_centre_provider:' + node["rack"]["dataCentre"]["provider"] or ''
        ic_provider_account_name = 'ic_provider_account_name:' + node["rack"]["providerAccount"]["name"] or ''
        ic_provider_account_provider = 'ic_provider_account_provider:' + node["rack"]["providerAccount"]["provider"] or ''
    tag_list = []
    for tag in [ic_node_id, ic_cluster_id, ic_public_ip, ic_private_ip, ic_rack_name, ic_data_centre_custom_name, ic_data_centre_name,
                ic_data_centre_provider, ic_provider_account_name, ic_provider_account_provider]:
        if tag != '':
            tag_list.append(tag)
    if 'AWS_VPC' in ic_data_centre_provider:
        tag_list = tag_list + [
            'region:' + node["rack"]["dataCentre"]["name"].lower().replace("_", "-"),
            'availability_zone:' + node["rack"]["name"]
        ]
    return tag_list
