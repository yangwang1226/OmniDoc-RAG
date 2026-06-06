# 使用官方 Python 3.11 作为基础镜像
FROM dir.staff.xdf.cn/xone-env/python:3.11

# 设置工作目录
WORKDIR /app

# 复制当前目录的内容到容器的 /app 目录下
COPY . /app

# 设置时区
COPY sources.list /etc/apt/sources.list

# 安装 LibreOffice 和字体相关包
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    libreoffice-writer \
    libreoffice-impress \
    libreoffice-common \
    fontconfig \
    fonts-noto-cjk \
    fonts-wqy-microhei \
    fonts-wqy-zenhei \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 复制本地 fonts 文件夹到容器的字体目录
COPY fonts/ /usr/share/fonts/windows/

# 更新字体缓存
RUN fc-cache -fv

# 验证安装
RUN soffice --version

# 安装 Python 依赖
RUN pip install --upgrade pip
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8000

CMD ["supervisord"]