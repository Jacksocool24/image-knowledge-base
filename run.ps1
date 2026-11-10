$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
& 'C:\Users\三十而立\AppData\Local\Programs\Python\Python312\python.exe' -m streamlit run app.py --server.headless true --server.address 127.0.0.1 --server.port 8504
