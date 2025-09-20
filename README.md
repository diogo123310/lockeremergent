# 🏪 Sistema de Luggage Storage Automático

Sistema completo de aluguel de cacifos automático com integração Stripe e controle via Raspberry Pi.

## 📁 Estrutura do Projeto

```
/app/
├── backend/
│   ├── server.py          # 🔧 API Principal - FastAPI + MongoDB
│   ├── requirements.txt   # 📦 Dependências Python
│   └── .env              # ⚙️ Variáveis de ambiente (Stripe, MongoDB)
├── frontend/
│   ├── src/
│   │   ├── App.js        # ⚛️ Aplicação React Principal
│   │   ├── App.css       # 🎨 Estilos customizados
│   │   └── components/ui/ # 🧩 Componentes shadcn/ui
│   ├── package.json      # 📦 Dependências Node.js
│   └── .env             # ⚙️ URL do backend
└── README.md            # 📖 Esta documentação
```

## 🚀 Como Executar para Desenvolvimento

### Backend (FastAPI)
```bash
cd /app/backend
pip install -r requirements.txt
# O servidor roda automaticamente via supervisor na porta 8001
```

### Frontend (React)
```bash
cd /app/frontend
yarn install
# O servidor roda automaticamente via supervisor na porta 3000
```
## 🔧 Configurações Importantes

### Variáveis de Ambiente
- **Backend (.env)**: MONGO_URL, STRIPE_API_KEY, DB_NAME
- **Frontend (.env)**: REACT_APP_BACKEND_URL

### Preços dos Cacifos (editar em server.py)
```python
LOCKER_PRICES = {
    LockerSize.SMALL: 2.0,   # €2.00 por 24h
    LockerSize.MEDIUM: 3.0,  # €3.00 por 24h
    LockerSize.LARGE: 5.0    # €5.00 por 24h
}
```

### Distribuição de Cacifos (editar função initialize_lockers)
- Cacifos 1-8: Pequenos
- Cacifos 9-16: Médios  
- Cacifos 17-24: Grandes

## 🎨 Personalização da Interface

### Cores Principais (App.css)
- Azul principal: `#3b82f6` (botões, ícones)
- Verde preços: `#16a34a` (valores monetários)
- Gradientes: `from-blue-50 to-indigo-100`

### Componentes UI (shadcn/ui)
Localizados em `/app/frontend/src/components/ui/`
- `button.jsx` - Botões do sistema
- `card.jsx` - Cards dos cacifos
- `input.jsx` - Campos de entrada
- `toast.jsx` - Notificações

## 🔌 Endpoints da API

### Principais Endpoints
- `GET /api/lockers/availability` - Lista disponibilidade
- `POST /api/rentals` - Cria novo aluguel
- `POST /api/lockers/unlock` - Desbloqueia cacifo
- `GET /api/payments/status/{session_id}` - Status pagamento

### Endpoints Admin
- `GET /api/admin/lockers` - Lista todos cacifos
- `GET /api/admin/rentals` - Lista todos aluguéis

## 🛠️ Hardware (Raspberry Pi)

### Conexões Recomendadas
```python
# Simulação atual em server.py linha ~380
print(f"HARDWARE: Unlocking locker {request.locker_number}")

# TODO: Implementar controle real via GPIO
# import RPi.GPIO as GPIO
# GPIO.setup(relay_pin, GPIO.OUT)
# GPIO.output(relay_pin, GPIO.HIGH)  # Ativar relé
```

### Pinos Sugeridos (24 cacifos)
- GPIO 2-25: Controle dos relés das fechaduras
- GPIO 26-27: LEDs de status (opcional)

## 💳 Stripe Integration

### Modo Teste vs Produção
```python
# Alterar em server.py para produção:
stripe_api_key = os.environ.get('STRIPE_LIVE_API_KEY')  # Chave de produção
```

### Webhooks
- URL: `https://seudominio.com/api/webhook/stripe`
- Eventos: `checkout.session.completed`

## 🚀 Deploy para Produção

### 1. Configurar Variáveis
```bash
# Backend
STRIPE_API_KEY=sk_live_... # Chave Stripe de produção
MONGO_URL=mongodb://... # MongoDB produção

# Frontend  
REACT_APP_BACKEND_URL=https://seudominio.com
```

### 2. Hardware Setup
- Instalar Raspberry Pi OS
- Conectar módulos relé
- Instalar dependências Python
- Configurar GPIO

### 3. Kiosk Setup
- Instalar touchscreen
- Configurar browser em fullscreen
- URL: `https://seudominio.com`

## 🐛 Debugging e Logs

### Backend logs
```bash
tail -f /var/log/supervisor/backend.*.log
```

### Frontend logs
```bash
tail -f /var/log/supervisor/frontend.*.log
```

### Testar APIs
```bash
curl -X GET https://seudominio.com/api/lockers/availability
```

## 📝 TODOs e Melhorias

### Funcionalidades
- [ ] Sistema de reservas antecipadas
- [ ] Notificações por email/SMS
- [ ] Dashboard administrativo web
- [ ] Sistema de descuentos/promoções
- [ ] Integração com câmeras de segurança

### Hardware
- [ ] Implementar controle GPIO real
- [ ] Sistema de sensores de ocupação
- [ ] Backup power para Raspberry Pi
- [ ] Sistema de monitoramento remoto

### UX/UI
- [ ] Modo escuro/claro
- [ ] Suporte multi-idioma
- [ ] Tutorial interativo
- [ ] Feedback tátil (vibração)

## 🆘 Problemas Comuns

### Cacifo não desbloqueou
1. Verificar se pagamento foi aprovado
2. Conferir código PIN
3. Verificar se não expirou (24h)
4. Testar endpoint unlock via curl

### Stripe não funciona
1. Verificar STRIPE_API_KEY no .env
2. Confirmar modo teste vs produção
3. Verificar webhooks configurados
4. Testar com cartão de teste Stripe

### Interface não carrega
1. Verificar REACT_APP_BACKEND_URL
2. Testar API endpoints diretamente
3. Verificar logs do supervisor
4. Reiniciar serviços: `sudo supervisorctl restart all`

## 📞 Suporte Técnico

Para dúvidas sobre desenvolvimento ou modificações, consulte:
- Documentação FastAPI: https://fastapi.tiangolo.com/
- Documentação React: https://react.dev/
- Documentação Stripe: https://stripe.com/docs
- Documentação shadcn/ui: https://ui.shadcn.com/

---
**Sistema desenvolvido com Emergent.sh** 🚀