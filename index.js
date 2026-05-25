const express = require('express');
const app = express();
const PORT = process.env.PORT || 3000;

app.use(express.json());
app.use(express.text());

// Store scripts in memory
const scripts = new Map();

// YOUR EXISTING GET ENDPOINT (keep this)
app.get('/getscript', (req, res) => {
  const userId = req.query.user;
  const script = scripts.get(userId);
  
  if (!script) {
    return res.status(404).send("-- Script not found");
  }
  
  res.setHeader('Content-Type', 'text/plain');
  res.send(script);
});

// NEW ENDPOINT: Host a script from file/lua code
app.post('/hostscript', (req, res) => {
  let code = req.body;
  
  // If sent as JSON with 'code' field
  if (req.body && req.body.code) {
    code = req.body.code;
  }
  
  // Auto-detect Lua code
  if (typeof code !== 'string') {
    return res.status(400).json({ error: "No code provided" });
  }
  
  // Generate unique ID
  const scriptId = Date.now().toString();
  scripts.set(scriptId, code);
  
  // Generate the loadstring URL (exactly like your example)
  const loadstringUrl = `loadstring(game:HttpGet("https://raul-scripts-bot-production.up.railway.app/getscript?user=${scriptId}"))()`;
  
  res.json({
    loadstring: loadstringUrl
  });
});

// Optional: Delete script (good for cleanup)
app.delete('/script/:id', (req, res) => {
  const id = req.params.id;
  if (scripts.delete(id)) {
    res.json({ success: true });
  } else {
    res.status(404).json({ error: "Script not found" });
  }
});

app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
  console.log(`Hosting ${scripts.size} scripts in memory`);
});
