from flask import Flask, jsonify, request
from dotenv import load_dotenv
from langchain.chains import RetrievalQA
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain.vectorstores import Chroma
from langchain.llms import GPT4All, LlamaCpp
import os
import logging

load_dotenv()

embeddings_model_name = os.environ.get("EMBEDDINGS_MODEL_NAME")
persist_directory = os.environ.get('PERSIST_DIRECTORY')

model_type = os.environ.get('MODEL_TYPE')
model_path = os.environ.get('MODEL_PATH')
model_n_ctx = os.environ.get('MODEL_N_CTX')
target_source_chunks = int(os.environ.get('TARGET_SOURCE_CHUNKS', 4))

from constants import CHROMA_SETTINGS

app = Flask(__name__)

# Set up the logger
logging.basicConfig(level=logging.DEBUG)

# Set debug mode
app.debug = True

@app.before_request
def log_request_info():
    app.logger.debug('Headers: %s', request.headers)
    app.logger.debug('Body: %s', request.get_data())

@app.after_request
def log_response_info(response):
    app.logger.debug('Response: %s', response.get_data(as_text=True))
    return response

def create_qa_pipeline():
    embeddings = HuggingFaceEmbeddings(model_name=embeddings_model_name)
    db = Chroma(persist_directory=persist_directory, embedding_function=embeddings, client_settings=CHROMA_SETTINGS)
    retriever = db.as_retriever(search_kwargs={"k": target_source_chunks})
    callbacks = [StreamingStdOutCallbackHandler()]
    if hasattr(request, 'mute_stream') and request.mute_stream:
        callbacks.clear()
    engine = None
    if model_type == "LlamaCpp":
        engine = LlamaCpp(model_path=model_path, n_ctx=model_n_ctx, callbacks=callbacks, verbose=False)
    elif model_type == "GPT4All":
        engine = GPT4All(model=model_path, n_ctx=model_n_ctx, backend='gptj', callbacks=callbacks, verbose=False)
    else:
        raise ValueError(f"Model {model_type} not supported!")
    qa = RetrievalQA.from_chain_type(llm=engine, chain_type="stuff", retriever=retriever, return_source_documents=not hasattr(request, 'hide_source') or not request.hide_source)
    return qa

@app.route('/api/qa', methods=['POST'])
def qa():
    req = request.get_json(force=True)
    query = req.get('query', '')
    qa_pipeline = create_qa_pipeline()
    res = qa_pipeline(query)
    answer, docs = res['result'], [] if hasattr(request, 'hide_source') and request.hide_source else res['source_documents']
    response = {
        "query": query,
        "result": answer,
    }
    if not hasattr(request, 'hide_source') or not request.hide_source:
        response['source_documents'] = [{"metadata": {"source": d.metadata.get('source', '')}, "page_content": d.page_content} for d in docs]
    return jsonify(response)

if __name__ == "__main__":
    app.run()