from pydantic import BaseModel


class CustomerMessageDraft(BaseModel):
    to: str
    subject: str
    body: str
    commitment_id: str
