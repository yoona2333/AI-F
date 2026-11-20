from tortoise import fields, models

class AssistantMessage(models.Model):

    id = fields.BigIntField(primary_key=True)
    role = fields.CharField(max_length=20)
    content = fields.TextField()


    class Meta:
        table = "assistant_message"