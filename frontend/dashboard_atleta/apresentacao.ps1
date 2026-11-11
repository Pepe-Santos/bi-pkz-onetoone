# Abre o dashboard com os dados ficticios da apresentacao, em http://localhost:8503.
# Nenhum dado real aparece: a variavel DADOS_FICTICIOS faz a tela ignorar o .env.
$env:DADOS_FICTICIOS = "1"
& "$PSScriptRoot\.venv\Scripts\python.exe" -m streamlit run "$PSScriptRoot\app.py" --server.port 8503
