"""
🏪 SISTEMA DE LUGGAGE STORAGE AUTOMÁTICO - API BACKEND
=======================================================

Este arquivo contém toda a lógica do backend para o sistema de cacifos automático.

ESTRUTURA PRINCIPAL:
📦 Models: Definições de dados (Locker, Rental, PaymentTransaction)
🔌 API Endpoints: Rotas para frontend e webhooks
💳 Stripe Integration: Pagamentos e verificação de status
🔧 Hardware Simulation: Controle das fechaduras (simulado)
⏰ Background Tasks: Verificação de expiração automática

COMO EDITAR:
- Preços: Alterar LOCKER_PRICES (linha ~95)
- Cacifos: Modificar initialize_lockers() (linha ~104)
- Hardware: Implementar controle GPIO em unlock_locker() (linha ~380)
- Webhooks: Configurar stripe_webhook() (linha ~410)
"""

from fastapi import FastAPI, APIRouter, HTTPException, Request, Header
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
import uuid
from datetime import datetime, timezone, timedelta
from emergentintegrations.payments.stripe.checkout import StripeCheckout, CheckoutSessionResponse, CheckoutStatusResponse, CheckoutSessionRequest
import asyncio
from enum import Enum

# ====================================
# 🔧 CONFIGURAÇÃO INICIAL
# ====================================

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Conexão com MongoDB
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Configuração Stripe (modo teste por padrão)
# TODO: Para produção, usar STRIPE_LIVE_API_KEY
stripe_api_key = os.environ.get('STRIPE_API_KEY')

# Criar aplicação FastAPI
app = FastAPI(
    title="Luggage Storage API",
    description="API para sistema de cacifos automático",
    version="1.0.0"
)

# Router com prefixo /api (importante para Kubernetes ingress)
api_router = APIRouter(prefix="/api")

# ====================================
# 📋 ENUMS E CONSTANTES
# ====================================

class LockerSize(str, Enum):
    """Tamanhos disponíveis de cacifos"""
    SMALL = "small"    # Pequeno - para bagagem de mão
    MEDIUM = "medium"  # Médio - para mochilas
    LARGE = "large"    # Grande - para malas grandes

class LockerStatus(str, Enum):
    """Status possíveis de um cacifo"""
    AVAILABLE = "available"      # Disponível para aluguel
    OCCUPIED = "occupied"        # Ocupado com pagamento pendente/aprovado
    MAINTENANCE = "maintenance"  # Em manutenção (desabilitado)

class PaymentStatus(str, Enum):
    """Status de pagamento"""
    PENDING = "pending"    # Aguardando pagamento
    SUCCESS = "success"    # Pagamento aprovado
    FAILED = "failed"      # Pagamento falhou
    EXPIRED = "expired"    # Sessão de pagamento expirou

# ====================================
# 💰 CONFIGURAÇÃO DE PREÇOS
# ====================================
# 🔍 EDITAR AQUI: Para alterar os preços dos cacifos
LOCKER_PRICES = {
    LockerSize.SMALL: 2.0,   # €2.00 por 24 horas
    LockerSize.MEDIUM: 3.0,  # €3.00 por 24 horas  
    LockerSize.LARGE: 5.0    # €5.00 por 24 horas
}

# ====================================
# 🗄️ MODELOS DE DADOS (PYDANTIC)
# ====================================

class Locker(BaseModel):
    """Modelo de dados para um cacifo individual"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    number: int                                    # Número físico do cacifo (1-24)
    size: LockerSize                              # Tamanho do cacifo
    status: LockerStatus = LockerStatus.AVAILABLE # Status atual
    current_rental_id: Optional[str] = None       # ID do aluguel ativo (se houver)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Rental(BaseModel):
    """Modelo de dados para um aluguel de cacifo"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    locker_id: str              # ID do cacifo alugado
    locker_number: int          # Número físico do cacifo
    locker_size: LockerSize     # Tamanho do cacifo
    access_pin: str             # PIN de 6 dígitos para acesso
    payment_session_id: Optional[str] = None  # ID da sessão Stripe
    payment_status: PaymentStatus = PaymentStatus.PENDING
    amount: float               # Valor pago em EUR
    currency: str = "EUR"       # Moeda (sempre EUR)
    start_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    end_time: datetime          # Fim do período de aluguel (24h após start_time)
    is_expired: bool = False    # Se o aluguel expirou
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class PaymentTransaction(BaseModel):
    """Modelo para registro de transações de pagamento"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str             # ID da sessão Stripe
    rental_id: str              # ID do aluguel relacionado
    amount: float               # Valor da transação
    currency: str               # Moeda da transação
    payment_status: PaymentStatus
    metadata: Dict              # Metadados adicionais do Stripe
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# ====================================
# 📥 MODELOS DE REQUEST/RESPONSE
# ====================================

class RentalRequest(BaseModel):
    """Request para criar um novo aluguel"""
    locker_size: LockerSize

class UnlockRequest(BaseModel):
    """Request para desbloquear um cacifo"""
    locker_number: int
    access_pin: str

class CheckoutRequest(BaseModel):
    """Request para checkout Stripe (interno)"""
    success_url: str
    cancel_url: str
    metadata: Optional[Dict] = {}

class LockerAvailability(BaseModel):
    """Response com disponibilidade de cacifos por tamanho"""
    size: LockerSize
    available_count: int
    price_per_24h: float

class RentalResponse(BaseModel):
    """Response após criar um aluguel"""
    rental_id: str
    checkout_url: str
    session_id: str

class UnlockResponse(BaseModel):
    """Response após tentar desbloquear cacifo"""
    success: bool
    message: str
    locker_number: Optional[int] = None

# ====================================
# 🚀 INICIALIZAÇÃO DO SISTEMA
# ====================================

async def initialize_lockers():
    """
    🔍 EDITAR AQUI: Para alterar distribuição de cacifos
    
    Inicializa os 24 cacifos se não existirem ainda.
    Distribuição atual:
    - Cacifos 1-8: Pequenos (SMALL)
    - Cacifos 9-16: Médios (MEDIUM)  
    - Cacifos 17-24: Grandes (LARGE)
    """
    existing_count = await db.lockers.count_documents({})
    if existing_count > 0:
        return
    
    lockers = []
    for i in range(1, 25):  # Cacifos numerados de 1 a 24
        if i <= 8:
            size = LockerSize.SMALL     # Primeiros 8: pequenos
        elif i <= 16:
            size = LockerSize.MEDIUM    # Próximos 8: médios
        else:
            size = LockerSize.LARGE     # Últimos 8: grandes
        
        locker = Locker(number=i, size=size)
        lockers.append(locker.dict())
    
    await db.lockers.insert_many(lockers)
    print(f"✅ Inicializados {len(lockers)} cacifos no sistema")

@app.on_event("startup")
async def startup_event():
    """Executado quando o servidor inicia"""
    await initialize_lockers()
    # Iniciar task em background para verificar aluguéis expirados
    asyncio.create_task(check_expired_rentals())

# ====================================
# ⏰ BACKGROUND TASKS
# ====================================

async def check_expired_rentals():
    """
    Task em background que roda constantemente para verificar e limpar aluguéis expirados.
    
    🔍 EDITAR AQUI: Para alterar frequência de verificação (atualmente 60 segundos)
    """
    while True:
        try:
            current_time = datetime.now(timezone.utc)
            
            # Buscar aluguéis que expiraram mas ainda não foram marcados como expirados
            expired_rentals = await db.rentals.find({
                "end_time": {"$lt": current_time},
                "is_expired": False,
                "payment_status": PaymentStatus.SUCCESS
            }).to_list(None)
            
            for rental in expired_rentals:
                # Marcar aluguel como expirado
                await db.rentals.update_one(
                    {"id": rental["id"]},
                    {"$set": {"is_expired": True}}
                )
                
                # Liberar o cacifo
                await db.lockers.update_one(
                    {"id": rental["locker_id"]},
                    {"$set": {
                        "status": LockerStatus.AVAILABLE,
                        "current_rental_id": None
                    }}
                )
                
                print(f"🔓 Aluguel expirado: Cacifo {rental['locker_number']} liberado automaticamente")
        
        except Exception as e:
            print(f"❌ Erro ao verificar aluguéis expirados: {e}")
        
        # Aguardar 60 segundos antes da próxima verificação
        # 🔍 EDITAR AQUI: Para alterar frequência (em segundos)
        await asyncio.sleep(60)

# ====================================
# 🛠️ FUNÇÕES UTILITÁRIAS
# ====================================

def generate_pin():
    """
    Gera um PIN de 6 dígitos para acesso ao cacifo.
    
    🔍 EDITAR AQUI: Para alterar formato do PIN (atualmente 6 dígitos)
    """
    import random
    return f"{random.randint(100000, 999999)}"

# ====================================
# 🔌 ENDPOINTS DA API
# ====================================

@api_router.get("/")
async def root():
    """Endpoint raiz da API"""
    return {"message": "Luggage Storage System API", "version": "1.0.0", "status": "running"}

@api_router.get("/lockers/availability", response_model=List[LockerAvailability])
async def get_locker_availability():
    """
    📊 ENDPOINT: Obter disponibilidade de cacifos
    
    Retorna quantos cacifos estão disponíveis para cada tamanho,
    junto com os preços por 24h.
    
    Used by: Homepage do frontend para exibir cards de seleção
    """
    availability = []
    
    for size in LockerSize:
        # Contar cacifos disponíveis deste tamanho
        available_count = await db.lockers.count_documents({
            "size": size,
            "status": LockerStatus.AVAILABLE
        })
        
        availability.append(LockerAvailability(
            size=size,
            available_count=available_count,
            price_per_24h=LOCKER_PRICES[size]
        ))
    
    return availability

@api_router.post("/rentals", response_model=RentalResponse)
async def create_rental(request: RentalRequest, http_request: Request):
    """
    🆕 ENDPOINT: Criar novo aluguel de cacifo
    
    Processo:
    1. Verificar disponibilidade
    2. Reservar cacifo temporariamente  
    3. Criar registro de aluguel
    4. Gerar sessão de pagamento Stripe
    5. Retornar URL de checkout
    
    Used by: Frontend quando usuário clica "Alugar Cacifo"
    """
    
    # 1. Verificar se há cacifos disponíveis do tamanho solicitado
    available_locker = await db.lockers.find_one({
        "size": request.locker_size,
        "status": LockerStatus.AVAILABLE
    })
    
    if not available_locker:
        raise HTTPException(
            status_code=400,
            detail=f"Não há cacifos {request.locker_size} disponíveis no momento"
        )
    
    # 2. Criar dados do aluguel
    rental = Rental(
        locker_id=available_locker["id"],
        locker_number=available_locker["number"],
        locker_size=request.locker_size,
        access_pin=generate_pin(),
        amount=LOCKER_PRICES[request.locker_size],
        end_time=datetime.now(timezone.utc) + timedelta(hours=24)  # 24h de uso
    )
    
    # 3. Reservar cacifo temporariamente (será confirmado após pagamento)
    await db.lockers.update_one(
        {"id": available_locker["id"]},
        {"$set": {
            "status": LockerStatus.OCCUPIED,
            "current_rental_id": rental.id
        }}
    )
    
    # 4. Salvar aluguel no banco
    await db.rentals.insert_one(rental.dict())
    
    # 5. Criar sessão de pagamento Stripe
    host_url = str(http_request.base_url).rstrip('/')
    success_url = f"{host_url}/payment-success?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{host_url}/payment-cancelled"
    
    stripe_checkout = StripeCheckout(
        api_key=stripe_api_key,
        webhook_url=f"{host_url}/api/webhook/stripe"
    )
    
    checkout_request = CheckoutSessionRequest(
        amount=rental.amount,
        currency="EUR",
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={
            "rental_id": rental.id,
            "locker_number": str(rental.locker_number),
            "access_pin": rental.access_pin
        }
    )
    
    session = await stripe_checkout.create_checkout_session(checkout_request)
    
    # 6. Atualizar aluguel com ID da sessão Stripe
    await db.rentals.update_one(
        {"id": rental.id},
        {"$set": {"payment_session_id": session.session_id}}
    )
    
    # 7. Criar registro de transação
    transaction = PaymentTransaction(
        session_id=session.session_id,
        rental_id=rental.id,
        amount=rental.amount,
        currency=rental.currency,
        payment_status=PaymentStatus.PENDING,
        metadata=checkout_request.metadata
    )
    
    await db.payment_transactions.insert_one(transaction.dict())
    
    print(f"✅ Aluguel criado: Cacifo {rental.locker_number}, PIN: {rental.access_pin}")
    
    return RentalResponse(
        rental_id=rental.id,
        checkout_url=session.url,
        session_id=session.session_id
    )

@api_router.get("/payments/status/{session_id}")
async def get_payment_status(session_id: str):
    """
    💳 ENDPOINT: Verificar status de pagamento
    
    Consulta o Stripe para verificar se o pagamento foi aprovado
    e atualiza o status no banco de dados.
    
    Used by: Frontend após retorno do Stripe (polling)
    """
    
    stripe_checkout = StripeCheckout(api_key=stripe_api_key, webhook_url="")
    
    try:
        # Consultar status no Stripe
        status_response = await stripe_checkout.get_checkout_status(session_id)
        
        # Buscar aluguel relacionado
        rental = await db.rentals.find_one({"payment_session_id": session_id})
        if not rental:
            raise HTTPException(status_code=404, detail="Aluguel não encontrado")
        
        # Atualizar transação no banco
        await db.payment_transactions.update_one(
            {"session_id": session_id},
            {"$set": {
                "payment_status": PaymentStatus.SUCCESS if status_response.payment_status == "paid" else PaymentStatus.PENDING,
                "updated_at": datetime.now(timezone.utc)
            }}
        )
        
        # Se pagamento aprovado, ativar aluguel
        if status_response.payment_status == "paid":
            await db.rentals.update_one(
                {"id": rental["id"]},
                {"$set": {"payment_status": PaymentStatus.SUCCESS}}
            )
            
            print(f"✅ Pagamento aprovado: Cacifo {rental['locker_number']}, PIN: {rental['access_pin']}")
            
            return {
                "payment_status": "paid",
                "rental_id": rental["id"],
                "locker_number": rental["locker_number"],
                "access_pin": rental["access_pin"],
                "end_time": rental["end_time"].isoformat()
            }
        
        return {
            "payment_status": status_response.payment_status,
            "status": status_response.status
        }
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro ao verificar pagamento: {str(e)}")

@api_router.post("/lockers/unlock", response_model=UnlockResponse)
async def unlock_locker(request: UnlockRequest):
    """
    🔓 ENDPOINT: Desbloquear cacifo com PIN
    
    Verifica se o PIN é válido e aciona o hardware para abrir o cacifo.
    
    🔍 EDITAR AQUI: Para implementar controle real do hardware (GPIO)
    
    Used by: Terminal de desbloqueio no frontend
    """
    
    # Buscar aluguel ativo com PIN e número do cacifo corretos
    rental = await db.rentals.find_one({
        "locker_number": request.locker_number,
        "access_pin": request.access_pin,
        "payment_status": PaymentStatus.SUCCESS,
        "is_expired": False
    })
    
    if not rental:
        return UnlockResponse(
            success=False,
            message="Código PIN inválido ou cacifo não encontrado"
        )
    
    # Verificar se não expirou (dupla verificação)
    current_time = datetime.now(timezone.utc)
    if current_time > rental["end_time"]:
        # Marcar como expirado
        await db.rentals.update_one(
            {"id": rental["id"]},
            {"$set": {"is_expired": True}}
        )
        
        # Liberar cacifo
        await db.lockers.update_one(
            {"number": request.locker_number},
            {"$set": {
                "status": LockerStatus.AVAILABLE,
                "current_rental_id": None
            }}
        )
        
        return UnlockResponse(
            success=False,
            message="Tempo de armazenamento expirado (24 horas)"
        )
    
    # =====================================
    # 🔧 CONTROLE DE HARDWARE - EDITAR AQUI
    # =====================================
    
    # SIMULAÇÃO (atual):
    print(f"🔓 HARDWARE: Desbloqueando cacifo {request.locker_number}")
    
    # TODO: Implementar controle real via Raspberry Pi GPIO
    # Exemplo de implementação real:
    # try:
    #     import RPi.GPIO as GPIO
    #     
    #     # Configurar GPIO para relé do cacifo
    #     relay_pin = get_relay_pin(request.locker_number)  # Função para mapear cacifo->pino
    #     GPIO.setmode(GPIO.BCM)
    #     GPIO.setup(relay_pin, GPIO.OUT)
    #     
    #     # Ativar relé (abrir fechadura)
    #     GPIO.output(relay_pin, GPIO.HIGH)
    #     await asyncio.sleep(2)  # Manter aberto por 2 segundos
    #     GPIO.output(relay_pin, GPIO.LOW)
    #     
    #     # Cleanup
    #     GPIO.cleanup()
    #     
    # except Exception as e:
    #     print(f"❌ Erro no hardware: {e}")
    #     return UnlockResponse(
    #         success=False,
    #         message="Erro no sistema de desbloqueio"
    #     )
    
    print(f"✅ Cacifo {request.locker_number} desbloqueado com sucesso")
    
    return UnlockResponse(
        success=True,
        message="Cacifo desbloqueado com sucesso",
        locker_number=request.locker_number
    )

@api_router.post("/webhook/stripe")
async def stripe_webhook(request: Request, stripe_signature: str = Header(None)):
    """
    🪝 ENDPOINT: Webhook do Stripe
    
    Recebe notificações do Stripe sobre mudanças no status de pagamento.
    Importante para garantir que o sistema seja atualizado mesmo se o usuário
    fechar o browser durante o pagamento.
    
    🔍 EDITAR AQUI: Para adicionar outros tipos de eventos do Stripe
    """
    
    body = await request.body()
    
    stripe_checkout = StripeCheckout(api_key=stripe_api_key, webhook_url="")
    
    try:
        webhook_response = await stripe_checkout.handle_webhook(body, stripe_signature)
        
        if webhook_response.event_type == "checkout.session.completed":
            # Atualizar transação
            await db.payment_transactions.update_one(
                {"session_id": webhook_response.session_id},
                {"$set": {
                    "payment_status": PaymentStatus.SUCCESS,
                    "updated_at": datetime.now(timezone.utc)
                }}
            )
            
            # Ativar aluguel
            await db.rentals.update_one(
                {"payment_session_id": webhook_response.session_id},
                {"$set": {"payment_status": PaymentStatus.SUCCESS}}
            )
            
            print(f"✅ Webhook: Pagamento confirmado para sessão {webhook_response.session_id}")
        
        return {"status": "success"}
    
    except Exception as e:
        print(f"❌ Erro no webhook: {e}")
        return {"status": "error", "message": str(e)}

# ====================================
# 🔧 ENDPOINTS ADMINISTRATIVOS
# ====================================

@api_router.get("/admin/lockers")
async def get_all_lockers():
    """
    👑 ADMIN: Listar todos os cacifos
    
    🔍 EDITAR AQUI: Para adicionar autenticação admin
    """
    lockers = await db.lockers.find({}, {"_id": 0}).to_list(None)
    return lockers

@api_router.get("/admin/rentals")
async def get_all_rentals():
    """
    👑 ADMIN: Listar todos os aluguéis
    
    🔍 EDITAR AQUI: Para adicionar autenticação admin
    """
    rentals = await db.rentals.find({}, {"_id": 0}).to_list(None)
    return rentals

# ====================================
# 🌐 CONFIGURAÇÃO FINAL DA APLICAÇÃO
# ====================================

# Incluir router com todas as rotas
app.include_router(api_router)

# Configurar CORS (Cross-Origin Resource Sharing)
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    """Executado quando o servidor é desligado"""
    client.close()
    print("🔌 Conexão com MongoDB fechada")

# ====================================
# 🏁 FIM DO ARQUIVO
# ====================================

"""
💡 DICAS PARA EDIÇÃO:

1. PREÇOS: Altere LOCKER_PRICES (linha ~95)
2. CACIFOS: Modifique initialize_lockers() (linha ~104) 
3. HARDWARE: Implemente controle GPIO em unlock_locker() (linha ~380)
4. TIMING: Ajuste check_expired_rentals() (linha ~140)
5. WEBHOOKS: Configure eventos em stripe_webhook() (linha ~410)

📚 DOCUMENTAÇÃO:
- FastAPI: https://fastapi.tiangolo.com/
- Stripe: https://stripe.com/docs
- MongoDB: https://docs.mongodb.com/
- Raspberry Pi GPIO: https://gpiozero.readthedocs.io/
"""