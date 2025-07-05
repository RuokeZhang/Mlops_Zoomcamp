FROM public.ecr.aws/lambda/python:3.9.2025.07.05.07
RUN pip install pipenv


# 复制依赖文件
COPY requirements.txt ./

# 使用 pip 安装依赖
RUN pip install --no-cache-dir -r requirements.txt

RUN pip install click

COPY ["lambda_function.py",  "./"] 
CMD ["lambda_function.lambda_handler"]