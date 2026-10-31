// Run with Node.js >=22 (also available inside the isolated n8n image).
const fs = require('fs');
const path = require('path');
const dir = process.argv[2] || path.join(__dirname, '..', 'workflows');
for (const file of fs.readdirSync(dir).filter(f => f.endsWith('.json'))) {
  const workflow = JSON.parse(fs.readFileSync(path.join(dir, file), 'utf8'));
  for (const node of workflow.nodes) {
    if (node.parameters.jsCode) new Function('$input', '$', '$execution', 'require', node.parameters.jsCode);
    for (const value of Object.values(node.parameters)) {
      // Full ={{ ... }} expressions, excluding mixed template extraBody.
      if (typeof value === 'string' && value.startsWith('={{') && value.endsWith('}}'))
        new Function('$input', '$', '$execution', 'return (' + value.slice(3, -2) + ')');
    }
  }
  console.log(file + ': código e expressões compilados');
  const validator = workflow.nodes.find(n => n.name === 'Langfuse - Validar Score da IA');
  if (validator) {
    const execute = items => new Function('$input', validator.parameters.jsCode)({all: () => items.map(json => ({json}))});
    const valid = execute([{text: JSON.stringify({score: 0.8, justificativa: 'Texto com "aspas" e barra \\ sintética.'})}]);
    if (valid[0].json.score !== 0.8) throw new Error('Validação de score escapado falhou');
    for (const score of [-1, 2, '0.8']) {
      if (execute([{score, justificativa: 'Sintética'}])[0].json.evaluation_status !== 'unavailable')
        throw new Error('Score inválido foi aceito');
    }
    console.log('Score: JSON escapado e rejeição de valores inválidos aprovados');
  }
}
