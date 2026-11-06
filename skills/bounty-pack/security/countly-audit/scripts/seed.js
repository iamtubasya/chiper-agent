// Countly seed — writes identities directly to MongoDB (no API round-trip).
// Run from INSIDE the countly dir on WSL so require('mongodb')/require('argon2') resolve
// against Countly's own node_modules.  Usage:  node seed.js
const mongodb = require('mongodb');
const argon2 = require('argon2');
const crypto = require('crypto');
function md5(s){ return crypto.createHash('md5').update(s+'').digest('hex'); }

const emptyPermission = { c:{}, r:{}, u:{}, d:{}, _:{ a:[], u:[[]] } };

async function main() {
  const client = new mongodb.MongoClient('mongodb://127.0.0.1:27017', { serverSelectionTimeoutMS: 5000 });
  await client.connect();
  const db = client.db('countly');
  const members = db.collection('members');
  const apps = db.collection('apps');

  // --- admin (global_admin) ---
  let adminApiKey;
  if (await members.countDocuments() > 0) {
    const a = await members.findOne({ username: 'testadmin' });
    adminApiKey = a && a.api_key;
  } else {
    adminApiKey = md5(crypto.randomBytes(48).toString('hex') + Math.random());
    await members.insertOne({
      full_name: 'Countly Test Admin', username: 'testadmin',
      password: await argon2.hash('Str0ng!Pass#countly2026'),
      email: 'testadmin@localhost.local', global_admin: true,
      created_at: Math.floor(Date.now()/1000), password_changed: Math.floor(Date.now()/1000),
      api_key: adminApiKey, permission: emptyPermission, locked: false,
    });
  }

  // --- two apps (tenant A + tenant B) ---
  async function ensureApp(name) {
    const existing = await apps.findOne({ name });
    if (existing) return { id: existing._id + '', key: existing.key };
    const key = md5(crypto.randomBytes(64).toString('hex') + Math.random() + Date.now());
    const app = { name, country:'US', timezone:'UTC', category:'0', key, id_key: key,
      keys: [{ key, added_at: Math.floor(Date.now()/1000), last_data: 0 }],
      created_at: Math.floor(Date.now()/1000), edited_at: Math.floor(Date.now()/1000),
      owner:'', seq:0, has_image:false, type:'mobile' };
    const ins = await apps.insertOne(app);
    await apps.createIndex({'keys.key':1}, { background:true });
    return { id: ins.insertedId + '', key };
  }
  const appA = await ensureApp('Test App');
  const appB = await ensureApp('Test App B');

  // --- non-admin members (for BOLA differential) ---
  async function ensureMember(username, permission) {
    const existing = await members.findOne({ username });
    if (existing) return existing.api_key;
    const apiKey = md5(crypto.randomBytes(48).toString('hex') + Math.random());
    await members.insertOne({
      full_name: username, username,
      password: await argon2.hash('Str0ng!Pass#' + username),
      email: username + '@localhost.local', global_admin: false,
      created_at: Math.floor(Date.now()/1000), password_changed: Math.floor(Date.now()/1000),
      api_key: apiKey, permission, locked: false,
    });
    return apiKey;
  }
  const userbKey = await ensureMember('userb', { c:{},r:{},u:{},d:{}, _:{ a:[], u:[[appA.id]] } }); // read-only on A
  const usercKey = await ensureMember('userc', emptyPermission);                                  // no access

  console.log(JSON.stringify({ adminApiKey, appA, appB, userbKey, usercKey }, null, 2));
  await client.close();
}
main().catch(e => { console.error('SERDFAIL', e); process.exit(1); });