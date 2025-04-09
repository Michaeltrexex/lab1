
const http = require('http');
const fs = require('fs');
const path = require('path');
const mysql = require('mysql2/promise');
const url = require('url');

const PORT = 3000;

const dbConfig = {
  host: 'localhost',
  user: 'root',
  password: 'root12',
  database: 'todolist',
};

async function retrieveListItems() {
  const connection = await mysql.createConnection(dbConfig);
  const [rows] = await connection.execute('SELECT id, text FROM items');
  await connection.end();
  return rows;
}

async function getHtmlRows() {
  const rows = await retrieveListItems();
  return rows.map((item, index) => `
    <tr>
      <td>${index + 1}</td>
      <td>${item.text}</td>
      <td>
        <button onclick="editItem(${item.id})">Edit</button>
        <button onclick="deleteItem(${item.id})">Delete</button>
      </td>
    </tr>
  `).join('');
}

async function addItemToDb(text) {
  const connection = await mysql.createConnection(dbConfig);
  const [result] = await connection.execute('INSERT INTO items (text) VALUES (?)', [text]);
  await connection.end();
  return { id: result.insertId, text };
}

async function deleteItemFromDb(id) {
  const connection = await mysql.createConnection(dbConfig);
  await connection.execute('DELETE FROM items WHERE id = ?', [id]);
  await connection.end();
}

async function updateItemInDb(id, newText) {
  const connection = await mysql.createConnection(dbConfig);
  await connection.execute('UPDATE items SET text = ? WHERE id = ?', [newText, id]);
  await connection.end();
}

const server = http.createServer(async (req, res) => {
  const parsedUrl = url.parse(req.url, true);
  if (req.method === 'GET' && parsedUrl.pathname === '/') {
    const htmlPath = path.join(__dirname, 'index.html');
    let html = fs.readFileSync(htmlPath, 'utf8');
    const rows = await getHtmlRows();
    html = html.replace('{{rows}}', rows);
    res.writeHead(200, { 'Content-Type': 'text/html' });
    res.end(html);
  } else if (req.method === 'POST' && parsedUrl.pathname === '/add-item') {
    let body = '';
    req.on('data', chunk => body += chunk);
    req.on('end', async () => {
      const { text } = JSON.parse(body);
      const result = await addItemToDb(text);
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ success: true, item: result }));
    });
  } else if (req.method === 'DELETE' && parsedUrl.pathname.startsWith('/delete-item/')) {
    const id = parsedUrl.pathname.split('/').pop();
    await deleteItemFromDb(id);
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ success: true }));
  } else if (req.method === 'PUT' && parsedUrl.pathname.startsWith('/edit-item/')) {
    const id = parsedUrl.pathname.split('/').pop();
    let body = '';
    req.on('data', chunk => body += chunk);
    req.on('end', async () => {
      const { text } = JSON.parse(body);
      await updateItemInDb(id, text);
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ success: true }));
    });
  } else if (req.method === 'GET') {
    const filePath = path.join(__dirname, parsedUrl.pathname);
    if (fs.existsSync(filePath)) {
      const ext = path.extname(filePath).toLowerCase();
      const contentType = ext === '.js' ? 'text/javascript' : 'text/plain';
      res.writeHead(200, { 'Content-Type': contentType });
      res.end(fs.readFileSync(filePath));
    } else {
      res.writeHead(404);
      res.end('Not Found');
    }
  } else {
    res.writeHead(404);
    res.end('Not Found');
  }
});

server.listen(PORT, () => {
  console.log(`Server is running on http://localhost:${PORT}`);
});
