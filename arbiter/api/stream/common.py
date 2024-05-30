from fastapi.datastructures import QueryParams


def extra_query_params(query_params: QueryParams) -> dict:
    extraParams = {}
    for k in query_params.keys():
        if k != 'token':
            extraParams[k] = query_params[k]
    return extraParams
