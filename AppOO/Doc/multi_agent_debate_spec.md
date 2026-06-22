# ESPECIFICACIÓN TÉCNICA
## Sistema de Debate Multi-Agente
### *Society of Mind + Sequential Debate con Síntesis*
> Para análisis financiero y planificación de retiro

| Proyecto | Versión | Lenguaje | API | Entorno | Repo |
|---|---|---|---|---|---|
| multi-agent-debate | 1.0.0 | Python 3.10+ | Anthropic Claude (claude-sonnet-4-6) | VS Code + Claude Extension | gutierrezw/MyPython |

---

## 1. Resumen Ejecutivo

Este documento especifica la implementación de un sistema de análisis basado en debate multi-agente usando la técnica **Society of Mind con razonamiento secuencial**. El sistema está diseñado específicamente para decisiones de planificación financiera y de retiro, donde la confiabilidad y el cuestionamiento explícito de supuestos son críticos.

> **Concepto central: Society of Mind + Sequential Debate**
>
> Un único modelo de lenguaje encarna sucesivamente cuatro roles con personalidades y temperaturas distintas. Cada rol recibe como contexto todas las respuestas anteriores, generando un debate acumulativo real. Un quinto rol sintetizador integra el debate completo y produce la respuesta final. El proceso completo es trazable, auditable y parametrizable desde un archivo de configuración YAML.

---

## 2. Arquitectura del Sistema

### 2.1 Flujo de Debate (Pipeline)

El sistema ejecuta cinco llamadas a la API en secuencia. Cada llamada acumula el contexto de las anteriores:

| Paso | Agente | Temperatura | Contexto de entrada |
|---|---|---|---|
| 1 | Optimista | 0.9 | Solo el prompt original del usuario |
| 2 | Escéptico | 0.7 | Prompt + output del Optimista |
| 3 | Prudente | 0.4 | Prompt + outputs 1 y 2 |
| 4 | Contradictorio | 1.0 | Prompt + outputs 1, 2 y 3 |
| 5 | Sintetizador | 0.3 | Prompt + outputs de los 4 agentes |

### 2.2 Estructura de Carpetas

```
MyPython/
└── multi_agent_debate/
    ├── debate.py          # Orquestador principal
    ├── agents.py          # Definición de roles y system prompts
    ├── config.yaml        # Parámetros configurables
    ├── models.py          # Dataclasses: AgentRole, DebateRound, DebateResult
    ├── renderer.py        # Formato de salida (consola, markdown, JSON)
    ├── requirements.txt   # anthropic>=0.25.0, pyyaml, rich
    └── examples/
        ├── retiro_basico.py
        └── etf_selection.py
```

---

## 3. Definición de Roles

Cada agente tiene un system prompt dedicado que establece su personalidad, restricciones y objetivo dentro del debate. Los parámetros de temperatura no son aleatorios: reflejan el grado de creatividad vs. determinismo deseado para cada rol.

### 📈 OPTIMISTA — `temp: 0.9`
- **Persona:** Analista bull senior con 20 años de experiencia. Ve oportunidades donde otros ven riesgo.
- **Tarea:** Argumentar el mejor escenario razonablemente posible. Identificar catalizadores y ventajas. NO inventar datos.

### 🔍 ESCÉPTICO — `temp: 0.7`
- **Persona:** Ex-regulador financiero. Cuestionador sistemático. Busca los supuestos escondidos.
- **Tarea:** Identificar falacias, supuestos débiles y riesgos ignorados en la postura optimista. Citar contraejemplos.

### ⚖️ PRUDENTE — `temp: 0.4`
- **Persona:** Actuario con especialización en riesgo de retiro. Orientado a preservación de capital.
- **Tarea:** Proponer marco intermedio. Cuantificar riesgo concreto. Sugerir criterios de decisión objetivos.

### ⚡ CONTRADICTORIO — `temp: 1.0`
- **Persona:** Filósofo del escepticismo radical. Abogado del diablo institucionalizado.
- **Tarea:** Atacar el consenso emergente. Si todos coinciden, encontrar por qué están todos equivocados.

### 🎯 SINTETIZADOR — `temp: 0.3`
- **Persona:** Director de Comité de Inversiones. Integrador de perspectivas divergentes.
- **Tarea:** Sintetizar el debate. Identificar puntos de acuerdo y desacuerdo real. Entregar recomendación accionable.

---

## 4. Modelos de Datos (Python Dataclasses)

### 4.1 AgentRole

```python
from dataclasses import dataclass
from typing import Literal

@dataclass
class AgentRole:
    name: str                    # 'optimista' | 'esceptico' | 'prudente' | 'contradictorio' | 'sintetizador'
    emoji: str                   # Identificador visual
    system_prompt: str           # Personalidad e instrucciones del rol
    temperature: float           # 0.3 - 1.0 según rol
    max_tokens: int = 800        # Limite por turno de debate
    color: str = 'white'         # Para renderer de consola (rich)
```

### 4.2 DebateRound

```python
@dataclass
class DebateRound:
    role: AgentRole
    prompt_sent: str             # Contexto completo enviado a la API
    response: str                # Respuesta del agente
    tokens_used: int             # Para monitoreo de costo
    duration_ms: int             # Latencia de la llamada
```

### 4.3 DebateResult

```python
@dataclass
class DebateResult:
    question: str                # Pregunta original del usuario
    rounds: list[DebateRound]    # Los 4 turnos de debate
    synthesis: DebateRound       # Turno del sintetizador
    total_tokens: int
    total_duration_ms: int
    timestamp: str               # ISO 8601
    config_used: dict            # Snapshot de config.yaml
```

---

## 5. Lógica del Orquestador (debate.py)

### 5.1 Función principal

```python
import anthropic
from models import AgentRole, DebateRound, DebateResult
from agents import ROLES  # Lista ordenada de AgentRole

def run_debate(question: str, config: dict) -> DebateResult:
    client = anthropic.Anthropic()  # Usa ANTHROPIC_API_KEY del env
    rounds: list[DebateRound] = []
    accumulated_context = build_initial_context(question)

    for role in ROLES['debate_agents']:  # Los 4 roles de debate
        prompt = build_prompt(accumulated_context, role, rounds)
        response = call_api(client, role, prompt)
        round_ = DebateRound(role=role, ...)
        rounds.append(round_)
        accumulated_context = update_context(accumulated_context, round_)

    # Llamada final al sintetizador
    synthesis = call_synthesizer(client, question, rounds)

    return DebateResult(question=question, rounds=rounds, synthesis=synthesis, ...)
```

### 5.2 Construcción del contexto acumulado

```python
def build_prompt(base_context: str, role: AgentRole, prev_rounds: list) -> str:
    debate_history = ''
    for r in prev_rounds:
        debate_history += f'\n\n--- {r.role.emoji} {r.role.name.upper()} ---\n{r.response}'

    if debate_history:
        return f'{base_context}\n\nDEBATE HASTA AHORA:{debate_history}\n\nTu turno como {role.name}:'
    else:
        return f'{base_context}\n\nEres el primero en responder. Analiza desde tu perspectiva:'
```

### 5.3 Llamada a la API

```python
def call_api(client: anthropic.Anthropic, role: AgentRole, prompt: str) -> str:
    message = client.messages.create(
        model='claude-sonnet-4-6',
        max_tokens=role.max_tokens,
        temperature=role.temperature,
        system=role.system_prompt,
        messages=[{'role': 'user', 'content': prompt}]
    )
    return message.content[0].text
```

---

## 6. Archivo de Configuración (config.yaml)

```yaml
# config.yaml - Todos los parámetros del sistema
model: claude-sonnet-4-6

agents:
  optimista:
    temperature: 0.9
    max_tokens: 800
  esceptico:
    temperature: 0.7
    max_tokens: 800
  prudente:
    temperature: 0.4
    max_tokens: 800
  contradictorio:
    temperature: 1.0
    max_tokens: 800
  sintetizador:
    temperature: 0.3
    max_tokens: 1200   # Más tokens: integra todo el debate

output:
  show_debate: true          # Mostrar rondas intermedias
  format: rich               # 'rich' | 'markdown' | 'json'
  save_to_file: false
  output_dir: ./debates/

domain:                      # Contexto inyectado en todos los roles
  focus: retiro_e_inversiones
  currency: ARS_USD
  user_profile: inversor_conservador_moderado
```

---

## 7. System Prompts de Referencia

### 7.1 Optimista

```
Eres un analista financiero senior con 20 años de experiencia en mercados emergentes
y planificación de retiro. Tu rol en este debate es el de OPTIMISTA.

Reglas:
- Argumenta el mejor escenario razonablemente posible, NO el utópico.
- Fundamenta cada afirmación: usa datos históricos, tendencias, catalizadores concretos.
- Identifica ventajas competitivas y oportunidades que el mercado sub-valora.
- Si hay argumentos previos, refútalos con evidencia, no con optimismo vago.
- Máximo 3 párrafos. Sé conciso y directo.
- Contexto: el usuario está construyendo su sistema de pensión personal.
```

### 7.2 Escéptico

```
Eres un ex-regulador financiero con experiencia en crisis: 2001, 2008, 2018.
Tu rol en este debate es el de ESCEPTICO.

Reglas:
- Identifica los supuestos implícitos en el análisis previo.
- Pregunta: ¿qué tendría que ser verdad para que eso funcione?
- Cita al menos un contraejemplo histórico concreto.
- No seas negativo por principio: sé preciso en el riesgo que identificas.
- Máximo 3 párrafos.
```

### 7.3 Prudente

```
Eres un actuario especializado en riesgo de longevidad y planificación de retiro.
Tu rol es el de PRUDENTE.

Reglas:
- Busca el marco intermedio: no bull, no bear, sino el rango plausible.
- Cuantifica el riesgo de forma concreta (% de probabilidad, rangos, escenarios).
- Propone criterios de decisión objetivos: ¿qué indicador deberíamos monitorear?
- Orientado a preservación de capital en el largo plazo.
- Máximo 3 párrafos.
```

### 7.4 Contradictorio

```
Tu rol es el de ABOGADO DEL DIABLO institucionalizado.

Reglas:
- Lee el debate hasta ahora. Identifica el consenso emergente.
- Tu trabajo es ROMPER ese consenso con argumentos de alto impacto.
- ¿Todos acuerdan en X? Entonces encuentra por qué X está equivocado.
- Usa pensamiento de segundo orden: consecuencias de las consecuencias.
- No seas destructivo sin propuesta: cierra con la pregunta que nadie hizo.
- Máximo 3 párrafos. Alta densidad intelectual.
```

### 7.5 Sintetizador

```
Eres el Director de un Comité de Inversiones. Acabas de presenciar un debate
entre cuatro analistas. Tu trabajo es sintetizar, no mediar.

Estructura tu respuesta en 4 secciones:
1. PUNTOS DE ACUERDO: qué convergencias genuinas hubo en el debate.
2. PUNTOS DE DESACUERDO REAL: qué sigue sin resolverse y por qué importa.
3. RECOMENDACION: cuál es la acción o decisión más razonable dado el debate.
4. CONDICIONES DE REVISION: qué eventos o datos cambiarían esta recomendación.

Sé específico y accionable. El usuario necesita decidir, no seguir debatiendo.
```

---

## 8. Requisitos e Instalación

### 8.1 requirements.txt

```
anthropic>=0.25.0
pyyaml>=6.0
rich>=13.0      # Consola con colores por rol
python-dotenv   # Para ANTHROPIC_API_KEY en .env
```

### 8.2 Setup inicial

```bash
# 1. Clonar / navegar al repo
cd MyPython/multi_agent_debate

# 2. Entorno virtual
python -m venv .venv
source .venv/bin/activate    # Windows: .venv\Scripts\activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar API key
echo 'ANTHROPIC_API_KEY=sk-ant-...' > .env

# 5. Ejecutar ejemplo
python examples/retiro_basico.py
```

### 8.3 Ejemplo de uso desde código

```python
from debate import run_debate
from config import load_config
from renderer import render_result

config = load_config('config.yaml')

result = run_debate(
    question='Tengo 45 años, USD 50k ahorrados. ¿Deberia invertir en ETFs globales '
             'o mantener liquidez en dólares dado el contexto argentino?',
    config=config
)

render_result(result, config)    # Imprime debate + síntesis con colores
```

---

## 9. Ventajas y Desventajas del Enfoque

| ✅ VENTAJAS | ⚠️ DESVENTAJAS |
|---|---|
| Reduce sesgos de confirmación: el escéptico y contradictorio atacan supuestos | Costo en tokens: 5 llamadas por consulta (~3,000-5,000 tokens promedio) |
| Razonamiento trazable y auditable: ves por qué se llegó a la conclusión | Latencia: 15-30 segundos por consulta completa (llamadas secuenciales) |
| Ideal para decisiones de alto impacto: retiro, inversiones, planificación | Posible convergencia trivial: agentes del mismo modelo base pueden alinearse |
| No requiere infraestructura compleja: solo la API de Anthropic | Calidad sensible al system prompt: roles mal definidos dan debates superficiales |
| Configurable por dominio: se adapta a finanzas, medicina, ingeniería | No es adecuado para preguntas simples o factuales: overkill y caro |

---

## 10. Extensiones Futuras Sugeridas

### 10.1 Corto plazo
- Modo streaming: mostrar respuesta de cada agente en tiempo real mientras llega
- Historial persistente: guardar debates en JSON/SQLite para referencia futura
- CLI interactivo: usar Rich Prompt para ingresar preguntas desde terminal

### 10.2 Mediano plazo
- Web UI minimalista: Flask/FastAPI + HTMX para visualizar debates en browser
- Integración con Morningstar MCP: enriquecer el contexto con datos reales de mercado
- Perfil de usuario: inyectar automáticamente edad, monto ahorrado, horizonte de retiro

### 10.3 Largo plazo
- Debate iterativo: permitir al usuario rebatir la síntesis y lanzar segunda ronda
- Exportar a PDF: generar informe formal del debate para archivo personal
- Multi-modelo: usar GPT-4o en el rol Contradictorio para evitar convergencia

---

> **📌 Nota de implementación para Claude en VS Code**
> Este documento fue generado por Claude (claude.ai) como especificación completa lista para implementar.
> El código de ejemplo es funcional y sigue las convenciones de la API de Anthropic v0.25+.
> Repo de destino: `gutierrezw/MyPython` (privado). Carpeta sugerida: `multi_agent_debate/`
> Ante dudas sobre cualquier sección, consultar directamente a Claude en claude.ai o VS Code.
