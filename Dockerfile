FROM public.ecr.aws/lambda/python:3.9

COPY requirements.txt .
RUN pip install torch==2.8.0 --index-url https://download.pytorch.org/whl/cpu -t .
RUN pip install --no-cache-dir -r requirements.txt -t .

COPY . .

CMD ["lambda_handler.lambda_handler"]
