import { useState } from 'react'

function Chat() {
  const [input, setInput] = useState('')
  const [messages, setMessages] = useState([])

  const validateMessage = (message) => {
    const trimmed = message.trim().toLowerCase()
    
    // Check for minimum length
    if (trimmed.length < 5) {
      return { valid: false, error: "Dit spørgsmål er for kort. Vær mere specifik." }
    }
    
    // Check for insurance-related content
    const insuranceTerms = [
      'forsikring', 'police', 'dækning', 'betingelser', 'præmie', 
      'selvrisiko', 'topdanmark', 'tryg', 'cna', 'hdi', 'selskab',
      'erstatning', 'skade', 'vilkår', 'sammenlign', 'forskelle'
    ]
    
    const hasInsuranceTerms = insuranceTerms.some(term => trimmed.includes(term))
    
    if (!hasInsuranceTerms) {
      return { 
        valid: false, 
        error: "Dit spørgsmål skal relatere til forsikring. Nævn forsikringsselskaber, policer eller sammenligning af forsikringer." 
      }
    }
    
    // Check for overly vague questions
    const vaguePhrases = ['hvad med', 'fortæl om', 'generelt', 'alt om', 'hej', 'hallo']
    const isVague = vaguePhrases.some(phrase => trimmed.startsWith(phrase))
    
    if (isVague) {
      return { 
        valid: false, 
        error: "Dit spørgsmål er for vagt. Stil et specifikt spørgsmål om forsikring eller sammenligning." 
      }
    }
    
    return { valid: true }
  }

  const sendMessage = async () => {
    if (!input.trim()) return

    console.log('🔵 Frontend: Sender besked:', input)
    
    // Validate message before sending
    const validation = validateMessage(input)
    if (!validation.valid) {
      const errorMessage = { 
        sender: 'bot', 
        text: `❌ ${validation.error}`,
        isError: true 
      }
      setMessages(prev => [...prev, { sender: 'user', text: input }, errorMessage])
      setInput('')
      return
    }
    
    const userMessage = { sender: 'user', text: input }
    setMessages(prev => [...prev, userMessage])

    setInput('')

    try {
      const requestBody = { message: input }
      console.log('🔵 Frontend: Request body:', requestBody)
      console.log('🔵 Frontend: Sender til URL:', 'http://localhost:8000/ask')
      
      const response = await fetch('http://localhost:8000/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestBody)
      })

      console.log('🔵 Frontend: Response status:', response.status)
      console.log('🔵 Frontend: Response headers:', response.headers)
      
      const data = await response.json()
      console.log('🔵 Frontend: Svar fra server (rå data):', data)
      console.log('🔵 Frontend: Type af svar:', typeof data)
      console.log('🔵 Frontend: data.answer:', data.answer)
      
      // Check if backend returned an error/validation message
      if (data.error) {
        const errorMessage = { 
          sender: 'bot', 
          text: `❌ ${data.error}`,
          isError: true 
        }
        setMessages(prev => [...prev, errorMessage])
        return
      }
      
      // Håndter forskellige typer af svar
      let displayText = data.answer || data.result || '[Ingen svar]'
      
      // Check for specific "I don't understand" responses from backend
      if (displayText.toLowerCase().includes('jeg forstår ikke') || 
          displayText.toLowerCase().includes('kan ikke besvare') ||
          displayText.toLowerCase().includes('ugyldigt spørgsmål')) {
        const clarificationMessage = { 
          sender: 'bot', 
          text: `${displayText}\n\n💡 Prøv at stille et mere specifikt spørgsmål om forsikring eller sammenligning af forsikringsselskaber.`,
          isError: true 
        }
        setMessages(prev => [...prev, clarificationMessage])
        return
      }
      
      // Check for repetitive content and warn user
      if (displayText.length > 1000) {
        const lines = displayText.split('\n')
        const uniqueLines = new Set(lines.filter(line => line.trim().length > 10))
        const repetitionRatio = (lines.length - uniqueLines.size) / lines.length
        
        if (repetitionRatio > 0.3) {
          console.log('🔵 Frontend: Repetitivt indhold detekteret')
          displayText += '\n\n⚠️ Bemærk: Svaret indeholder muligvis gentagelser. Dette kan skyldes model-begrænsninger.'
        }
      }
      
      // Hvis det er en sammenligning, vis ekstra info
      if (data.type === 'compare') {
        const subtype = data.subtype || 'sammenligning'
        const prefix = `📊 ${subtype.replace('_', ' ').toUpperCase()}\n\n`
        displayText = prefix + displayText
        
        // Vis antal kilder hvis tilgængelig
        if (data.sources_count) {
          displayText += `\n\n📚 Baseret på ${data.sources_count} kilder`
        }
      }

      const assistantMessage = { sender: 'assistant', text: displayText }
      setMessages(prev => [...prev, assistantMessage])
    } catch (error) {
      console.error('🔴 Frontend: Fejl ved afsendelse:', error)
      const errorMessage = { sender: 'assistant', text: `Fejl: ${error.message}` }
      setMessages(prev => [...prev, errorMessage])
    }
  }

  return (
    <div>
      <div style={{ 
        border: '1px solid #ccc', 
        padding: '10px', 
        minHeight: '300px', 
        marginBottom: '10px',
        maxHeight: '500px',
        overflowY: 'auto'
      }}>
        {messages.map((msg, idx) => (
          <div key={idx} style={{ 
            textAlign: msg.sender === 'user' ? 'right' : 'left',
            marginBottom: '10px',
            padding: '8px',
            backgroundColor: msg.sender === 'user' ? '#e3f2fd' : '#f5f5f5',
            borderRadius: '8px',
            maxWidth: '80%',
            marginLeft: msg.sender === 'user' ? 'auto' : '0',
            marginRight: msg.sender === 'user' ? '0' : 'auto'
          }}>
            <strong style={{ color: msg.sender === 'user' ? '#1976d2' : '#388e3c' }}>
              {msg.sender === 'user' ? '👤 Du' : '🤖 Assistent'}:
            </strong> 
            <div style={{ 
              marginTop: '5px', 
              whiteSpace: 'pre-wrap',
              lineHeight: '1.4'
            }}>
              {msg.text}
            </div>
          </div>
        ))}
      </div>

      <div style={{ display: 'flex', gap: '10px' }}>
        <input
          type="text"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyPress={e => e.key === 'Enter' && sendMessage()}
          placeholder="Skriv din besked (prøv: 'sammenlign Tryg og Topdanmark')"
          style={{ 
            flex: 1,
            padding: '10px',
            borderRadius: '5px',
            border: '1px solid #ccc'
          }}
        />
        <button 
          onClick={sendMessage}
          style={{
            padding: '10px 20px',
            backgroundColor: '#1976d2',
            color: 'white',
            border: 'none',
            borderRadius: '5px',
            cursor: 'pointer'
          }}
        >
          Send
        </button>
      </div>
    </div>
  )
}

export default Chat
