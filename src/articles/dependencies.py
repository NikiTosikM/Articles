from fastapi import Request


def get_redis_man(request: Request):
    return request.app.state.redis_man


def get_postgre_man(request: Request):
    return request.app.state.postgre_man


def get_request_man(request: Request):
    return request.app.state.request_man