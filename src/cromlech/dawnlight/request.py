# -*- coding: utf-8 -*-

try:
    import grokcore.component
    from cromlech.dawnlight import IDawnlightApplication
    from cromlech.io.interfaces import IRequest, IResponse
    from cromlech.request.webob_req import Request, Response
    from cromlech.request.webob_req import IWebObRequest, IWebObResponse

    @grokcore.component.adapter(IWebObRequest, IDawnlightApplication)
    @grokcore.component.implementer(IRequest)
    def make_webob_request(request, app):
        return Request(request, request.script_name)

    @grokcore.component.adapter(IWebObResponse)
    @grokcore.component.implementer(IResponse)
    def make_webob_response(response):
        return Response(response)

except ImportError:
    pass
