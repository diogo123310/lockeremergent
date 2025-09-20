import React, { useState, useEffect } from "react";
import "./App.css";
import { BrowserRouter, Routes, Route, useSearchParams, useLocation } from "react-router-dom";
import axios from "axios";
import { Button } from "./components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "./components/ui/card";
import { Badge } from "./components/ui/badge";
import { Input } from "./components/ui/input";
import { Label } from "./components/ui/label";
import { AlertCircle, Lock, Package, Check, Clock, Euro } from "lucide-react";
import { Alert, AlertDescription } from "./components/ui/alert";
import { useToast } from "./hooks/use-toast";
import { Toaster } from "./components/ui/toaster";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const LockerSelection = () => {
  const [availability, setAvailability] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedSize, setSelectedSize] = useState(null);
  const [isRenting, setIsRenting] = useState(false);
  const { toast } = useToast();

  useEffect(() => {
    fetchAvailability();
  }, []);

  const fetchAvailability = async () => {
    try {
      const response = await axios.get(`${API}/lockers/availability`);
      setAvailability(response.data);
    } catch (error) {
      console.error("Error fetching availability:", error);
      toast({
        title: "Erro",
        description: "Não foi possível carregar a disponibilidade dos cacifos",
        variant: "destructive"
      });
    } finally {
      setLoading(false);
    }
  };

  const getSizeDisplayName = (size) => {
    const names = {
      small: "Pequeno",
      medium: "Médio", 
      large: "Grande"
    };
    return names[size] || size;
  };

  const getSizeIcon = (size) => {
    if (size === "small") return "📦";
    if (size === "medium") return "📋";
    return "🧳";
  };

  const handleRent = async (size) => {
    if (isRenting) return;
    
    setIsRenting(true);
    setSelectedSize(size);

    try {
      const response = await axios.post(`${API}/rentals`, {
        locker_size: size
      });

      // Redirect to Stripe checkout
      window.location.href = response.data.checkout_url;
    } catch (error) {
      console.error("Error creating rental:", error);
      toast({
        title: "Erro",
        description: error.response?.data?.detail || "Erro ao criar reserva",
        variant: "destructive"
      });
      setIsRenting(false);
      setSelectedSize(null);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin w-12 h-12 border-4 border-blue-500 border-t-transparent rounded-full mx-auto mb-4"></div>
          <p className="text-gray-600 font-medium">Carregando cacifos disponíveis...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 p-4">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="text-center mb-12 pt-8">
          <div className="flex items-center justify-center mb-6">
            <div className="bg-blue-600 p-4 rounded-full mr-4">
              <Lock className="w-8 h-8 text-white" />
            </div>
            <h1 className="text-4xl font-bold text-gray-800">Sistema de Cacifos Automático</h1>
          </div>
          <p className="text-xl text-gray-600 max-w-3xl mx-auto">
            Armazene suas bagagens com segurança. Sistema automatizado com pagamento por cartão e acesso por código PIN.
          </p>
        </div>

        {/* Locker Selection */}
        <div className="grid md:grid-cols-3 gap-8 mb-12">
          {availability.map((locker) => (
            <Card 
              key={locker.size} 
              className={`relative overflow-hidden transition-all duration-300 hover:shadow-xl ${
                selectedSize === locker.size && isRenting 
                  ? 'ring-4 ring-blue-500 bg-blue-50' 
                  : 'hover:shadow-lg'
              }`}
            >
              <CardHeader className="text-center pb-2">
                <div className="text-6xl mb-4">{getSizeIcon(locker.size)}</div>
                <CardTitle className="text-2xl font-bold text-gray-800">
                  Cacifo {getSizeDisplayName(locker.size)}
                </CardTitle>
                <CardDescription className="text-lg">
                  <div className="flex items-center justify-center mt-2">
                    <Euro className="w-5 h-5 mr-1 text-green-600" />
                    <span className="text-2xl font-bold text-green-600">
                      {locker.price_per_24h.toFixed(2)}
                    </span>
                    <span className="text-gray-500 ml-1">/ 24h</span>
                  </div>
                </CardDescription>
              </CardHeader>
              
              <CardContent className="text-center">
                <div className="mb-6">
                  <Badge 
                    variant={locker.available_count > 0 ? "default" : "destructive"}
                    className="text-lg px-4 py-2"
                  >
                    {locker.available_count} disponíveis
                  </Badge>
                </div>
                
                <Button 
                  onClick={() => handleRent(locker.size)}
                  disabled={locker.available_count === 0 || isRenting}
                  className="w-full h-14 text-lg font-semibold bg-blue-600 hover:bg-blue-700 disabled:bg-gray-300"
                >
                  {selectedSize === locker.size && isRenting ? (
                    <div className="flex items-center">
                      <div className="animate-spin w-5 h-5 border-2 border-white border-t-transparent rounded-full mr-2"></div>
                      Processando...
                    </div>
                  ) : locker.available_count > 0 ? (
                    <>
                      <Package className="w-5 h-5 mr-2" />
                      Alugar Cacifo
                    </>
                  ) : (
                    "Indisponível"
                  )}
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>

        {/* Features */}
        <div className="bg-white rounded-2xl shadow-lg p-8 mb-8">
          <h2 className="text-2xl font-bold text-center mb-6 text-gray-800">Como Funciona</h2>
          <div className="grid md:grid-cols-3 gap-8">
            <div className="text-center">
              <div className="bg-blue-100 p-4 rounded-full w-16 h-16 mx-auto mb-4 flex items-center justify-center">
                <span className="text-2xl font-bold text-blue-600">1</span>
              </div>
              <h3 className="font-semibold text-lg mb-2">Escolha o Tamanho</h3>
              <p className="text-gray-600">Selecione o cacifo ideal para suas bagagens</p>
            </div>
            <div className="text-center">
              <div className="bg-green-100 p-4 rounded-full w-16 h-16 mx-auto mb-4 flex items-center justify-center">
                <span className="text-2xl font-bold text-green-600">2</span>
              </div>
              <h3 className="font-semibold text-lg mb-2">Faça o Pagamento</h3>
              <p className="text-gray-600">Pague com segurança através do terminal Stripe</p>
            </div>
            <div className="text-center">
              <div className="bg-purple-100 p-4 rounded-full w-16 h-16 mx-auto mb-4 flex items-center justify-center">
                <span className="text-2xl font-bold text-purple-600">3</span>
              </div>
              <h3 className="font-semibold text-lg mb-2">Receba seu PIN</h3>
              <p className="text-gray-600">Use o código para abrir e fechar o cacifo</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

const PaymentSuccess = () => {
  const [searchParams] = useSearchParams();
  const [paymentData, setPaymentData] = useState(null);
  const [loading, setLoading] = useState(true);
  const { toast } = useToast();

  useEffect(() => {
    const sessionId = searchParams.get('session_id');
    if (sessionId) {
      checkPaymentStatus(sessionId);
    }
  }, [searchParams]);

  const checkPaymentStatus = async (sessionId, attempts = 0) => {
    const maxAttempts = 10;
    
    if (attempts >= maxAttempts) {
      setLoading(false);
      toast({
        title: "Erro",
        description: "Não foi possível verificar o status do pagamento",
        variant: "destructive"
      });
      return;
    }

    try {
      const response = await axios.get(`${API}/payments/status/${sessionId}`);
      
      if (response.data.payment_status === 'paid') {
        setPaymentData(response.data);
        setLoading(false);
      } else {
        // Continue polling
        setTimeout(() => checkPaymentStatus(sessionId, attempts + 1), 2000);
      }
    } catch (error) {
      console.error('Error checking payment status:', error);
      if (attempts < maxAttempts - 1) {
        setTimeout(() => checkPaymentStatus(sessionId, attempts + 1), 2000);
      } else {
        setLoading(false);
        toast({
          title: "Erro",
          description: "Erro ao verificar status do pagamento",
          variant: "destructive"
        });
      }
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-green-50 to-emerald-100 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin w-12 h-12 border-4 border-green-500 border-t-transparent rounded-full mx-auto mb-4"></div>
          <p className="text-gray-600 font-medium">Verificando pagamento...</p>
        </div>
      </div>
    );
  }

  if (!paymentData) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-red-50 to-rose-100 flex items-center justify-center">
        <Card className="max-w-md mx-auto">
          <CardHeader>
            <CardTitle className="text-red-600 flex items-center">
              <AlertCircle className="w-6 h-6 mr-2" />
              Erro no Pagamento
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p>Não foi possível processar seu pagamento. Tente novamente.</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-green-50 to-emerald-100 flex items-center justify-center p-4">
      <Card className="max-w-2xl mx-auto shadow-2xl">
        <CardHeader className="text-center pb-6">
          <div className="bg-green-500 w-20 h-20 rounded-full flex items-center justify-center mx-auto mb-4">
            <Check className="w-10 h-10 text-white" />
          </div>
          <CardTitle className="text-3xl font-bold text-green-600 mb-2">
            Pagamento Confirmado!
          </CardTitle>
          <CardDescription className="text-lg">
            Seu cacifo foi reservado com sucesso
          </CardDescription>
        </CardHeader>
        
        <CardContent className="space-y-6">
          <div className="bg-green-50 p-6 rounded-lg border-2 border-green-200">
            <h3 className="text-xl font-bold text-center mb-4">Seus Dados de Acesso</h3>
            
            <div className="grid grid-cols-2 gap-4 mb-4">
              <div className="text-center">
                <Label className="text-sm text-gray-600">Número do Cacifo</Label>
                <div className="text-3xl font-bold text-blue-600">
                  {paymentData.locker_number}
                </div>
              </div>
              <div className="text-center">
                <Label className="text-sm text-gray-600">Código PIN</Label>
                <div className="text-3xl font-bold text-green-600 font-mono tracking-wider">
                  {paymentData.access_pin}
                </div>
              </div>
            </div>
            
            <Alert className="bg-yellow-50 border-yellow-200">
              <Clock className="w-4 h-4" />
              <AlertDescription>
                <strong>Atenção:</strong> Guarde bem estes dados! O cacifo expira em 24 horas 
                ({new Date(paymentData.end_time).toLocaleString('pt-PT')})
              </AlertDescription>
            </Alert>
          </div>
          
          <div className="text-center space-y-4">
            <p className="text-gray-600">
              Use o número do cacifo e o código PIN no terminal para abrir seu cacifo.
            </p>
            <Button 
              onClick={() => window.location.href = '/unlock'}
              className="bg-blue-600 hover:bg-blue-700 text-white px-8 py-3 text-lg"
            >
              <Lock className="w-5 h-5 mr-2" />
              Ir para Terminal de Acesso
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

const UnlockTerminal = () => {
  const [lockerNumber, setLockerNumber] = useState('');
  const [accessPin, setAccessPin] = useState('');
  const [isUnlocking, setIsUnlocking] = useState(false);
  const [result, setResult] = useState(null);
  const { toast } = useToast();

  const handleUnlock = async (e) => {
    e.preventDefault();
    
    if (!lockerNumber || !accessPin) {
      toast({
        title: "Erro",
        description: "Por favor, preencha o número do cacifo e o código PIN",
        variant: "destructive"
      });
      return;
    }

    setIsUnlocking(true);
    setResult(null);

    try {
      const response = await axios.post(`${API}/lockers/unlock`, {
        locker_number: parseInt(lockerNumber),
        access_pin: accessPin
      });

      setResult(response.data);
    } catch (error) {
      console.error('Error unlocking locker:', error);
      toast({
        title: "Erro",
        description: "Erro ao tentar desbloquear o cacifo",
        variant: "destructive"
      });
    } finally {
      setIsUnlocking(false);
    }
  };

  const resetForm = () => {
    setLockerNumber('');
    setAccessPin('');
    setResult(null);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-slate-200 flex items-center justify-center p-4">
      <Card className="max-w-md mx-auto shadow-2xl">
        <CardHeader className="text-center">
          <div className="bg-blue-600 w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4">
            <Lock className="w-8 h-8 text-white" />
          </div>
          <CardTitle className="text-2xl font-bold text-gray-800">
            Terminal de Acesso
          </CardTitle>
          <CardDescription>
            Insira os dados para abrir seu cacifo
          </CardDescription>
        </CardHeader>
        
        <CardContent>
          {result ? (
            <div className="text-center space-y-4">
              {result.success ? (
                <div className="space-y-4">
                  <div className="bg-green-500 w-16 h-16 rounded-full flex items-center justify-center mx-auto">
                    <Check className="w-8 h-8 text-white" />
                  </div>
                  <h3 className="text-xl font-bold text-green-600">
                    Cacifo Desbloqueado!
                  </h3>
                  <p className="text-gray-600">
                    Cacifo {result.locker_number} foi desbloqueado com sucesso.
                  </p>
                  <p className="text-sm text-yellow-600 font-medium">
                    ⚠️ O cacifo fechará automaticamente após alguns segundos
                  </p>
                </div>
              ) : (
                <div className="space-y-4">
                  <div className="bg-red-500 w-16 h-16 rounded-full flex items-center justify-center mx-auto">
                    <AlertCircle className="w-8 h-8 text-white" />
                  </div>
                  <h3 className="text-xl font-bold text-red-600">
                    Acesso Negado
                  </h3>
                  <p className="text-gray-600">
                    {result.message}
                  </p>
                </div>
              )}
              
              <Button 
                onClick={resetForm}
                className="w-full bg-blue-600 hover:bg-blue-700"
              >
                Tentar Novamente
              </Button>
            </div>
          ) : (
            <form onSubmit={handleUnlock} className="space-y-6">
              <div>
                <Label htmlFor="lockerNumber" className="text-sm font-medium">
                  Número do Cacifo
                </Label>
                <Input
                  id="lockerNumber"
                  type="number"
                  value={lockerNumber}
                  onChange={(e) => setLockerNumber(e.target.value)}
                  placeholder="Ex: 15"
                  className="text-center text-2xl h-14 mt-2"
                  min="1"
                  max="24"
                />
              </div>
              
              <div>
                <Label htmlFor="accessPin" className="text-sm font-medium">
                  Código PIN
                </Label>
                <Input
                  id="accessPin"
                  type="text"
                  value={accessPin}
                  onChange={(e) => setAccessPin(e.target.value.replace(/\D/g, '').slice(0, 6))}
                  placeholder="000000"
                  className="text-center text-2xl h-14 mt-2 font-mono tracking-widest"
                  maxLength="6"
                />
              </div>
              
              <Button 
                type="submit"
                disabled={isUnlocking}
                className="w-full h-14 text-lg bg-blue-600 hover:bg-blue-700"
              >
                {isUnlocking ? (
                  <div className="flex items-center">
                    <div className="animate-spin w-5 h-5 border-2 border-white border-t-transparent rounded-full mr-2"></div>
                    Desbloqueando...
                  </div>
                ) : (
                  <>
                    <Lock className="w-5 h-5 mr-2" />
                    Desbloquear Cacifo
                  </>
                )}
              </Button>
            </form>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

const PaymentCancelled = () => {
  return (
    <div className="min-h-screen bg-gradient-to-br from-red-50 to-rose-100 flex items-center justify-center p-4">
      <Card className="max-w-md mx-auto">
        <CardHeader className="text-center">
          <div className="bg-red-500 w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4">
            <AlertCircle className="w-8 h-8 text-white" />
          </div>
          <CardTitle className="text-2xl font-bold text-red-600">
            Pagamento Cancelado
          </CardTitle>
          <CardDescription>
            O pagamento foi cancelado. Nenhum cacifo foi reservado.
          </CardDescription>
        </CardHeader>
        
        <CardContent className="text-center">
          <Button 
            onClick={() => window.location.href = '/'}
            className="bg-blue-600 hover:bg-blue-700"
          >
            Voltar aos Cacifos
          </Button>
        </CardContent>
      </Card>
    </div>
  );
};

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<LockerSelection />} />
          <Route path="/payment-success" element={<PaymentSuccess />} />
          <Route path="/payment-cancelled" element={<PaymentCancelled />} />
          <Route path="/unlock" element={<UnlockTerminal />} />
        </Routes>
      </BrowserRouter>
      <Toaster />
    </div>
  );
}

export default App;