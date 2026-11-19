from langchain_core.prompts import ChatPromptTemplate

PROMPTS = {
    # Java 角色：学习水平进入系统规则，问题进入用户消息。
    "java": ChatPromptTemplate.from_messages([
        ("system", "你是一位 Python 助教。学生水平是{audience}。用中文先解释概念，再给一个小例子，最后说明一个常见错误。不要编造不存在的 API。"),
        ("human", "{question}"),
    ]),
    # 翻译角色：目标语言进入系统规则，正文进入用户消息。
    "translator": ChatPromptTemplate.from_messages([
        ("system", "你是一位翻译官。把用户提供的文本翻译成{targetLanguage}，保留原意和段落。只返回翻译结果，不添加解释。"),
        ("human", "{question}"),
    ]),
    # 文案角色：商品名进入系统规则，卖点进入用户消息。
    "copywriter": ChatPromptTemplate.from_messages([
        ("system", "你是一位数码商城文案写手。商品是{productName}。根据用户提供的真实卖点写一段简短中文文案。不要虚构价格、折扣、认证或售后承诺。"),
        ("human", "{question}"),
    ]),
}