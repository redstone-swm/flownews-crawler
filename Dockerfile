FROM public.ecr.aws/lambda/python:3.9

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -t .

COPY . .

CMD ["lambda_handler.lambda_handler"]
