from fastapi import FastAPI, Request, Response

from sydney_planner.agent.core import PlannerAgent
from sydney_planner.config import get_settings
from sydney_planner.utils.formatting import markdown_to_whatsapp


def register_whatsapp_routes(app: FastAPI, agent: PlannerAgent) -> None:
    settings = get_settings()

    @app.post("/webhook/whatsapp")
    async def whatsapp_webhook(request: Request):
        # Validate Twilio signature when credentials are configured
        if settings.twilio_auth_token:
            from twilio.request_validator import RequestValidator
            validator = RequestValidator(settings.twilio_auth_token)
            form = await request.form()
            url = str(request.url)
            signature = request.headers.get("X-Twilio-Signature", "")
            if not validator.validate(url, dict(form), signature):
                return Response(content="Forbidden", status_code=403)
        else:
            form = await request.form()

        from_number = form.get("From", "")
        body = form.get("Body", "").strip()

        if not body:
            return Response(content="", media_type="text/plain")

        user_id = f"whatsapp:{from_number}"
        reply = await agent.chat(user_id, body, "whatsapp")
        safe_reply = markdown_to_whatsapp(reply)

        # Respond with TwiML
        from twilio.twiml.messaging_response import MessagingResponse
        twiml = MessagingResponse()
        twiml.message(safe_reply)
        return Response(content=str(twiml), media_type="application/xml")
