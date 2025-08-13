# Usar uma imagem oficial do Python como base
FROM python:3.12-slim

# Definir variáveis de ambiente para Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Definir o diretório de trabalho dentro do contêiner
WORKDIR /app


# Copiar e instalar as dependências primeiro (otimiza o cache do Docker)
# O contexto do build foi definido como './backend' no docker-compose.yml.
# Portanto, os caminhos aqui são relativos a essa pasta.
COPY requirements.txt .
# Atualiza o pip e instala as dependências. --no-cache-dir é bom para manter a imagem pequena.
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt



# Expõe a porta que o Gunicorn vai usar

#EXPOSE 8000

# O comando final para iniciar a aplicação em produção com Gunicorn
#CMD ["gunicorn", "core.wsgi:application", "--bind", "0.0.0.0:8000"]
