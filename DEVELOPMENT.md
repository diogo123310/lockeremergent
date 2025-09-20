# 🛠️ Guia de Desenvolvimento - Visual Studio Code

Este documento contém instruções específicas para desenvolver e modificar o sistema usando VS Code.

## 🚀 Setup Inicial para Desenvolvimento

### 1. Extensões Recomendadas para VS Code

```json
{
  "recommendations": [
    "ms-python.python",
    "ms-python.black-formatter",
    "bradlc.vscode-tailwindcss",
    "esbenp.prettier-vscode",
    "ms-vscode.vscode-json",
    "PKief.material-icon-theme",
    "formulahendry.auto-rename-tag",
    "christian-kohler.path-intellisense"
  ]
}
```

### 2. Configuração do Workspace (.vscode/settings.json)

```json
{
  "python.defaultInterpreterPath": "/root/.venv/bin/python",
  "python.formatting.provider": "black",
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": false,
  "python.linting.flake8Enabled": true,
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.organizeImports": true
  },
  "tailwindCSS.includeLanguages": {
    "javascript": "javascript",
    "html": "HTML"
  },
  "emmet.includeLanguages": {
    "javascript": "javascriptreact"
  }
}
```

## 📁 Estrutura de Arquivos com Comentários

```
/app/
├── 📖 README.md                    # Documentação geral
├── 📖 DEVELOPMENT.md              # Este arquivo
├── backend/
│   ├── 🐍 server.py               # API Principal (MUITO COMENTADO)
│   ├── 📦 requirements.txt        # Dependências Python
│   └── ⚙️ .env                   # Variáveis de ambiente
├── frontend/
│   ├── src/
│   │   ├── ⚛️ App.js             # React Principal (MUITO COMENTADO)
│   │   ├── 🎨 App.css            # Estilos (MUITO COMENTADO)
│   │   └── components/ui/         # Componentes shadcn/ui
│   ├── 📦 package.json           # Dependências Node.js
│   └── ⚙️ .env                   # URL do backend
└── tests/                         # Testes automatizados
```

## 🔧 Como Editar Diferentes Partes

### 💰 Alterar Preços dos Cacifos

**Arquivo:** `/app/backend/server.py`
**Linha:** ~95

```python
# 🔍 EDITAR AQUI: Para alterar os preços dos cacifos
LOCKER_PRICES = {
    LockerSize.SMALL: 2.0,   # €2.00 por 24 horas
    LockerSize.MEDIUM: 3.0,  # €3.00 por 24 horas  
    LockerSize.LARGE: 5.0    # €5.00 por 24 horas
}
```

### 🏪 Alterar Quantidade/Distribuição de Cacifos

**Arquivo:** `/app/backend/server.py`
**Função:** `initialize_lockers()` (linha ~140)

```python
# Distribuição atual:
# - Cacifos 1-8: Pequenos (SMALL)
# - Cacifos 9-16: Médios (MEDIUM)  
# - Cacifos 17-24: Grandes (LARGE)

for i in range(1, 25):  # Mudar para mais/menos cacifos
    if i <= 8:          # Ajustar ranges
        size = LockerSize.SMALL
    elif i <= 16:
        size = LockerSize.MEDIUM
    else:
        size = LockerSize.LARGE
```

### 🎨 Alterar Cores da Interface

**Arquivo:** `/app/frontend/src/App.css`
**Seção:** Variáveis CSS (linha ~50)

```css
:root {
  /* Cores principais do sistema */
  --primary-blue: #3b82f6;      /* Azul dos botões */
  --primary-green: #16a34a;     /* Verde para preços */
  --primary-red: #dc2626;       /* Vermelho para erros */
  
  /* Gradientes de fundo */
  --gradient-blue: linear-gradient(135deg, #dbeafe 0%, #e0e7ff 100%);
}
```

### 📱 Alterar Textos da Interface

**Arquivo:** `/app/frontend/src/App.js`

**Título principal** (linha ~150):
```javascript
<h1 className="text-4xl font-bold text-gray-800">
  Sistema de Cacifos Automático  {/* Alterar aqui */}
</h1>
```

**Nomes dos tamanhos** (linha ~70):
```javascript
const getSizeDisplayName = (size) => {
  const names = {
    small: "Pequeno",    // Alterar aqui
    medium: "Médio",     // Alterar aqui
    large: "Grande"      // Alterar aqui
  };
  return names[size] || size;
};
```

### 🔧 Implementar Controle Real do Hardware

**Arquivo:** `/app/backend/server.py`
**Função:** `unlock_locker()` (linha ~380)

```python
# TODO: Implementar controle real via Raspberry Pi GPIO
# try:
#     import RPi.GPIO as GPIO
#     
#     # Configurar GPIO para relé do cacifo
#     relay_pin = get_relay_pin(request.locker_number)
#     GPIO.setmode(GPIO.BCM)
#     GPIO.setup(relay_pin, GPIO.OUT)
#     
#     # Ativar relé (abrir fechadura)
#     GPIO.output(relay_pin, GPIO.HIGH)
#     await asyncio.sleep(2)  # Manter aberto por 2 segundos
#     GPIO.output(relay_pin, GPIO.LOW)
#     
#     GPIO.cleanup()
# except Exception as e:
#     return UnlockResponse(success=False, message="Erro no hardware")
```

### ⏰ Alterar Tempo de Expiração

**Arquivo:** `/app/backend/server.py`

**Tempo de aluguel** (linha ~270):
```python
end_time=datetime.now(timezone.utc) + timedelta(hours=24)  # Mudar aqui
```

**Frequência de verificação** (linha ~160):
```python
await asyncio.sleep(60)  # Mudar para outros valores (em segundos)
```

## 🐛 Debugging no VS Code

### 1. Debug do Backend (FastAPI)

**Criar:** `.vscode/launch.json`

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Debug Backend",
      "type": "python",
      "request": "launch",
      "program": "/root/.venv/bin/uvicorn",
      "args": ["server:app", "--host", "0.0.0.0", "--port", "8001", "--reload"],
      "cwd": "${workspaceFolder}/backend",
      "console": "integratedTerminal"
    }
  ]
}
```

### 2. Debug do Frontend (React)

```json
{
  "name": "Debug Frontend",
  "type": "node",
  "request": "launch",
  "cwd": "${workspaceFolder}/frontend", 
  "runtimeExecutable": "yarn",
  "runtimeArgs": ["start"]
}
```

### 3. Breakpoints Recomendados

**Backend:**
- `create_rental()` - linha ~240 (criação de aluguel)
- `unlock_locker()` - linha ~350 (desbloqueio)
- `get_payment_status()` - linha ~300 (verificação pagamento)

**Frontend:**
- `handleRent()` - linha ~100 (processo de aluguel)
- `checkPaymentStatus()` - linha ~200 (polling pagamento)
- `handleUnlock()` - linha ~400 (desbloqueio)

## 🧪 Testes e Validação

### 1. Testar API com REST Client (VS Code)

**Criar:** `tests/api.http`

```http
### Verificar disponibilidade
GET https://lockit.preview.emergentagent.com/api/lockers/availability

### Criar aluguel
POST https://lockit.preview.emergentagent.com/api/rentals
Content-Type: application/json

{
  "locker_size": "small"
}

### Desbloquear cacifo
POST https://lockit.preview.emergentagent.com/api/lockers/unlock
Content-Type: application/json

{
  "locker_number": 1,
  "access_pin": "123456"
}
```

### 2. Logs em Tempo Real

**Terminal 1 - Backend:**
```bash
tail -f /var/log/supervisor/backend.*.log
```

**Terminal 2 - Frontend:**  
```bash
tail -f /var/log/supervisor/frontend.*.log
```

## 📊 Monitoramento Durante Desenvolvimento

### 1. Task no VS Code para Logs

**Criar:** `.vscode/tasks.json`

```json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "Watch Backend Logs",
      "type": "shell",
      "command": "tail -f /var/log/supervisor/backend.*.log",
      "group": "build",
      "presentation": {
        "echo": true,
        "reveal": "always",
        "panel": "new"
      }
    },
    {
      "label": "Restart Services",
      "type": "shell", 
      "command": "sudo supervisorctl restart all",
      "group": "build"
    }
  ]
}
```

### 2. Snippets Úteis

**Criar:** `.vscode/snippets.json`

```json
{
  "FastAPI Endpoint": {
    "prefix": "api-endpoint",
    "body": [
      "@api_router.${1:get}(\"/${2:endpoint}\")",
      "async def ${3:function_name}(${4:params}):",
      "    \"\"\"",
      "    ${5:Description}",
      "    \"\"\"",
      "    try:",
      "        ${6:logic}",
      "        return {\"success\": True}",
      "    except Exception as e:",
      "        raise HTTPException(status_code=400, detail=str(e))"
    ]
  },
  "React Component": {
    "prefix": "react-component",
    "body": [
      "const ${1:ComponentName} = () => {",
      "  const [${2:state}, set${2/(.*)/${1:/capitalize}/}] = useState(${3:initialValue});",
      "",
      "  useEffect(() => {",
      "    ${4:effect}",
      "  }, []);",
      "",
      "  return (",
      "    <div className=\"${5:classes}\">",
      "      ${6:content}",
      "    </div>",
      "  );",
      "};"
    ]
  }
}
```

## 🚀 Deploy e Produção

### 1. Checklist Pré-Deploy

- [ ] Alterar `STRIPE_API_KEY` para chave de produção
- [ ] Configurar `MONGO_URL` para MongoDB de produção
- [ ] Testar todos os endpoints
- [ ] Verificar logs de erro
- [ ] Testar interface em diferentes dispositivos
- [ ] Configurar backup do banco de dados

### 2. Configuração de Produção

**Backend (.env):**
```env
STRIPE_API_KEY=sk_live_...  # Chave de produção
MONGO_URL=mongodb://prod-server:27017
DB_NAME=luggage_storage_prod
CORS_ORIGINS=https://seudominio.com
```

**Frontend (.env):**
```env
REACT_APP_BACKEND_URL=https://api.seudominio.com
```

## 📞 Suporte e Recursos

### Documentação Oficial:
- **FastAPI:** https://fastapi.tiangolo.com/
- **React:** https://react.dev/
- **Tailwind CSS:** https://tailwindcss.com/
- **shadcn/ui:** https://ui.shadcn.com/

### Comandos Úteis:

```bash
# Reiniciar serviços
sudo supervisorctl restart all

# Ver status dos serviços  
sudo supervisorctl status

# Instalar nova dependência Python
pip install nome-pacote && pip freeze > requirements.txt

# Instalar nova dependência Node.js
cd frontend && yarn add nome-pacote

# Testar API
curl -X GET https://lockit.preview.emergentagent.com/api/lockers/availability

# Ver logs em tempo real
tail -f /var/log/supervisor/*.log
```

---

**💡 Dica:** Mantenha este arquivo atualizado sempre que fizer modificações significativas no sistema!