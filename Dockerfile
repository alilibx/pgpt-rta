FROM python:3

WORKDIR /

COPY requirements.txt ./

RUN pip install --no-cache-dir -r requirements.txt

RUN apt-get update && apt-get install -y inotify-tools

RUN mkdir -p source_documents

COPY start.sh .

RUN chmod +x start.sh

COPY . .

CMD ["bash", "start.sh"]
