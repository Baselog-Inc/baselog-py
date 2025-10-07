# Phase 1: Core API Integration Architecture (Week 1-2)

## Package Structure et Rôles Détaillés

### 1.1 Création du Package API (`src/baselog/api/`)

Le package API sera l'interface centralisée de communication avec le backend baselog, gérant toutes les opérations réseau de manière robuste et configurable.

**Composants Principaux :**

### `client.py` - Client HTTP Principal
**Rôle :** Cœur de l'inférence réseau, responsable de toutes les communications HTTP.

**Responsabilités :**
- Gestion des requêtes HTTP vers les endpoints baselog
- Configuration des timeouts (30s par défaut)
- Gestion des retry logic avec exponential backoff
- Implementation de connection pooling
- Validation des réponses et des codes HTTP
- Gestion des headers d'authentification
- Traitement des erreurs réseau et API

**Méthodes Clés :**
```python
class APIClient:
    async def send_log(log_data: LogModel) -> APIResponse:  # POST /projects/logs
    async def send_event(event_data: EventModel) -> APIResponse:  # Reserved for future
    async def health_check() -> bool:  # Optional /health endpoint
    async def close()
```

### `config.py` - Gestion de Configuration
**Rôle :** Centralisateur de toute la configuration dynamique de l'API.

**Responsabilités :**
- Chargement des variables d'environnement
- Validation des paramètres obligatoires (API key, base URL)
- Gestion des configurations par environment (dev/staging/prod)
- Validation de la configuration au démarrage
- Fourniture de configurations aux autres modules

**Paramètres Gérés :**
- `BASE_API_URL`: URL de base de l'API
- `API_KEY`: Clé API pour authentification
- `TIMEOUT`: Timeout des requêtes
- `RETRY_COUNT`: Nombre de tentatives en cas d'échec
- `BATCH_SIZE`: Taille des batchs pour l'envoi

### `auth.py` - Gestion d'Authentification
**Rôle :** Couche sécurisée de gestion des identifiants et de l'authentification.

**Responsabilités :**
- Validation et formatage de la clé API
- Génération des headers d'authentification (spécifiquement 'X-API-Key: {key}')
- Cryptage/décryptage des credentials sensibles
- Logging sécurisé des opérations d'auth

**Méthodes Clés :**
```python
class AuthManager:
    def validate_api_key(api_key: str) -> bool
    def get_auth_headers() -> Dict[str, str]:  # Returns {'X-API-Key': api_key, ...}
```


### `exceptions.py` - Exceptions Spécifiques à l'API
**Rôle :** Hiérarchie personnalisée des exceptions pour une gestion d'erreur fine.

**Types d'Exceptions :**
- `APIConnectionError`: Erreurs réseau
- `APIAuthenticationError`: Erreurs d'authentification
- `APITimeoutError`: Timeouts
- `APIRateLimitError`: Rate limiting
- `APIServerError`: Erreurs serveur (5xx)
- `APIClientError`: Erreurs client (4xx)

**Avantages :**
- Gestion différenciée des erreurs
- Messages d'erreur informatifs
- Stack traces propres
- Gestion facile dans les handlers

### 1.2 Implémentation du Client HTTP

**Architecture :**
- Utilisation de `httpx` pour le support async/sync
- Connection pooling pour les performances
- Timeout configurable par type de requête
- Retry strategy configurable avec jitter

**Caractéristiques Techniques :**
```python
# Configuration des retries avec dataclass pour robustesse et type safety
from dataclasses import dataclass, field
from typing import List

@dataclass
class RetryStrategy:
    max_attempts: int = 3
    backoff_factor: float = 1.0
    status_forcelist: List[int] = field(default_factory=lambda: [429, 500, 502, 503, 504])
    allowed_methods: List[str] = field(default_factory=lambda: ['POST', 'PUT', 'PATCH'])

    def to_dict(self) -> dict:
        return {k: getattr(self, k) for k in self.__dataclass_fields__}

# Usage:
retry_strategy = RetryStrategy()
# Pass to a custom retry handler or httpx limits

# Gestion des timeouts avec dataclass pour robustesse et type safety
from dataclasses import dataclass
from typing import Optional

@dataclass
class Timeouts:
    connect: float = 10.0
    read: float = 30.0
    write: float = 30.0
    pool: float = 60.0

    def to_dict(self) -> dict:
        return {k: getattr(self, k) for k in self.__dataclass_fields__}

# Usage:
timeouts = Timeouts()
httpx.Timeout(**timeouts.to_dict())
```

### 1.3 Modèles de Données

### `models.py` - Modèles de Sérialisation
**Rôle :** Définition stricte des structures de données pour communication API.

**LogModel (Structure) :**  # Matches backend schema: minimal required fields
```python
@dataclass
class LogModel:
    level: str  # e.g., "info", "error" (string as per backend)
    message: str
    category: Optional[str] = None  # Required in spec but optional in model
    tags: List[str] = field(default_factory=list)
    # Optional enhancements (added by client if backend supports; filter if not):
    timestamp: Optional[datetime] = field(default_factory=datetime.utcnow)
    service_name: Optional[str] = None
    user_id: Optional[str] = None
    correlation_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = field(default_factory=dict)
```

**EventModel (Structure) :**
```python
@dataclass
class EventModel:
    event_type: str
    payload: Dict[str, Any]
    timestamp: datetime
    source_service: str
    user_id: Optional[str] = None
    correlation_id: Optional[str] = None
```

### `responses.py` - Modèles de Réponse
**Rôle :** Normalisation des réponses et gestion des erreurs API.

**APIResponse (Succès) :**
```python
@dataclass
class APIResponse:
    success: bool
    data: Optional[Dict[str, Any]] = None
    message: Optional[str] = None
    request_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
```

**APIError (Erreur) :**
```python
@dataclass
class APIError:
    error_code: str
    message: str
    details: Optional[Dict[str, Any]] = None
    http_status: int
    retry_after: Optional[int] = None  # Pour rate limiting
```

## Intégration avec le Logger Existant

**Points d'Intégration :**
- Remplacement des `print()` statements par `api_client.send_log()`
- Conservation de l'API publique existante (`info()`, `debug()`, etc.)
- Ajout de configuration par environment variables
- Gestion des erreurs avec fallback console en cas d'échec

**Exemple d'Utilisation :**
```python
# Configuration initiale
from baselog.api import APIClient
from baselog.api.config import load_config

config = load_config()
client = APIClient(config)

# Intégration dans le Logger
class Logger:
    def __init__(self):
        self.api_client = client

    def info(self, message: str, **kwargs):
        log_data = LogModel(
            level="INFO",
            message=message,
            **kwargs
        )
        return self.api_client.send_log(log_data)
```

## Configuration par Défaut

**Variables d'Environnement :**
```bash
# Configuration de base
BASELOG_API_BASE_URL=https://baselog-api.vercel.app
BASELOG_API_KEY=your_api_key_here
BASELOG_ENVIRONMENT=development

# Performance
BASELOG_REQUEST_TIMEOUT=30
BASELOG_RETRY_COUNT=3
BASELOG_BATCH_SIZE=100
BASELOG_BATCH_INTERVAL=5
```

Cette architecture de Phase 1 fournit une base solide pour l'intégration API tout en maintenant la compatibilité avec le code existant.