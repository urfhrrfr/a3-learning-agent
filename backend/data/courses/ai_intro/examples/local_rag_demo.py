documents = {
    "ai_intro/ch04#concepts": "机器学习关注从数据中学习规律，并在新样本上泛化。",
    "ai_intro/ch11#rag": "RAG 通过先检索资料再生成回答来降低无来源内容的风险。",
}


def retrieve(query):
    return [doc_id for doc_id, text in documents.items() if any(word in text for word in query.split())]


query = "机器学习 泛化"
for doc_id in retrieve(query):
    print(doc_id, documents[doc_id])
