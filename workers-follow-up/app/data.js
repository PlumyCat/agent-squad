/* ============================================================
   Claude Squad — mock data + live simulation seed
   Plain JS, attaches to window.CSQ. The backend is not built yet;
   this stands in for the future workers / tickets / signals API.
   ============================================================ */
(function () {
  const now = Date.now();
  const ago = (ms) => new Date(now - ms);
  const S = 1000, M = 60 * S, H = 60 * M;

  // ── Status dictionaries ───────────────────────────────────
  const WORKER_STATUS = {
    running: { label: 'En cours',   cls: 'st-running', icon: 'bolt' },
    waiting: { label: 'En attente', cls: 'st-waiting', icon: 'pending' },
    blocked: { label: 'Bloqué',     cls: 'st-blocked', icon: 'block' },
    idle:    { label: 'Inactif',    cls: 'st-idle',    icon: 'pause_circle' },
    done:    { label: 'Terminé',    cls: 'st-done',    icon: 'check_circle' },
    exited:  { label: 'Sorti',      cls: 'st-exited',  icon: 'logout' },
    unknown: { label: 'Inconnu',    cls: 'st-unknown', icon: 'help' },
  };
  const TICKET_STATUS = {
    'open':        { label: 'Ouvert',  cls: 'st-open',       icon: 'radio_button_unchecked' },
    'in-progress': { label: 'En cours', cls: 'st-inprogress', icon: 'autorenew' },
    'waiting':     { label: 'En attente', cls: 'st-waiting', icon: 'pending' },
    'blocked':     { label: 'Bloqué',  cls: 'st-blocked',    icon: 'block' },
    'done':        { label: 'Terminé', cls: 'st-done',       icon: 'check_circle' },
  };
  const AGENTS = { codex: 'Codex', claude: 'Claude' };

  // ── Workers ───────────────────────────────────────────────
  // Claude Agent Teams in-process workers. Shape mirrors /api/state:
  // id = "name@team", agent: 'claude', session = id, team set, killable
  // (in-process teammates are never killable). Two teams illustrate Eric's
  // parallel-stories use case (the aggregated multi-team view groups by team).
  // status: running | waiting | blocked | idle | done | exited | unknown
  const workers = [
    // ── Team: checkout-revamp ─────────────────────────────
    {
      id: 'atlas@checkout-revamp', name: 'atlas', agent: 'claude', session: 'atlas@checkout-revamp',
      team: 'checkout-revamp', killable: false,
      status: 'waiting', role: 'Worker', ticket_id: 'CSQ-142',
      created_at: ago(38 * M), last_activity_at: ago(46 * S), exit_code: null,
      output: 'Dois-je migrer aussi les anciens enregistrements ou seulement les nouveaux ? J\'attends ta confirmation avant de continuer.',
      waiting_question: 'Migrer les enregistrements existants vers le nouveau schéma, ou seulement les créations futures ?',
    },
    {
      id: 'orion@checkout-revamp', name: 'orion', agent: 'claude', session: 'orion@checkout-revamp',
      team: 'checkout-revamp', killable: false,
      status: 'blocked', role: 'Worker', ticket_id: 'CSQ-138',
      created_at: ago(2 * H + 12 * M), last_activity_at: ago(9 * M), exit_code: null,
      output: 'npm run build → ÉCHEC. Type error in src/auth/session.ts:88. Impossible de continuer sans résolution des types.',
    },
    {
      id: 'nova@checkout-revamp', name: 'nova', agent: 'claude', session: 'nova@checkout-revamp',
      team: 'checkout-revamp', killable: false,
      status: 'running', role: 'Worker', ticket_id: 'CSQ-145',
      created_at: ago(17 * M), last_activity_at: ago(3 * S), exit_code: null,
      output: 'Running playwright spec checkout.e2e.ts … 12/18 passed',
    },
    {
      id: 'rhea@checkout-revamp', name: 'rhea', agent: 'claude', session: 'rhea@checkout-revamp',
      team: 'checkout-revamp', killable: false,
      status: 'done', role: 'Worker', ticket_id: 'CSQ-133',
      created_at: ago(3 * H), last_activity_at: ago(31 * M), exit_code: 0,
      output: 'Tâche terminée. 4 fichiers modifiés, 1 ajouté. Tous les tests passent (42/42).',
    },
    // ── Team: webhooks-v2 ─────────────────────────────────
    {
      id: 'vega@webhooks-v2', name: 'vega', agent: 'claude', session: 'vega@webhooks-v2',
      team: 'webhooks-v2', killable: false,
      status: 'running', role: 'Worker', ticket_id: null,
      created_at: ago(6 * M), last_activity_at: ago(2 * S), exit_code: null,
      output: 'grep -r "legacy_token" → 23 occurrences. Cartographie des usages en cours…',
    },
    {
      id: 'echo@webhooks-v2', name: 'echo', agent: 'claude', session: 'echo@webhooks-v2',
      team: 'webhooks-v2', killable: false,
      status: 'running', role: 'Worker', ticket_id: 'CSQ-141',
      created_at: ago(24 * M), last_activity_at: ago(8 * S), exit_code: null,
      output: 'Écriture de docs/api/webhooks.md … section "retries" ajoutée.',
    },
    {
      id: 'kilo@webhooks-v2', name: 'kilo', agent: 'claude', session: 'kilo@webhooks-v2',
      team: 'webhooks-v2', killable: false,
      status: 'idle', role: 'Worker', ticket_id: null,
      created_at: ago(1 * H + 5 * M), last_activity_at: ago(22 * M), exit_code: null,
      output: 'En attente d\'une tâche assignée.',
    },
  ];

  // ── Tickets (Linear-style ids) ────────────────────────────
  // status: open | in-progress | waiting | blocked | done
  const tickets = [
    {
      id: 'CSQ-142', title: 'Migrer le schéma des sessions vers le format v2',
      status: 'waiting', assigned_to: 'atlas',
      created_at: ago(40 * M), updated_at: ago(46 * S),
      body: 'Mettre à jour la table `sessions` pour utiliser le nouveau format de token. Conserver la rétro-compatibilité pendant 30 jours.',
      labels: ['backend', 'migration'], priority: 'high',
      history: [
        { t: ago(40 * M), who: 'eric', text: 'Ticket créé et assigné à atlas (claude).' },
        { t: ago(33 * M), who: 'atlas', text: 'Statut → En cours. Analyse du schéma actuel.' },
        { t: ago(46 * S), who: 'atlas', text: 'Statut → En attente. Question posée à l\'orchestrateur.' },
      ],
      comments: [
        { t: ago(2 * M), who: 'atlas', agent: true, text: 'J\'ai besoin d\'une décision sur la migration des données existantes.' },
      ],
    },
    {
      id: 'CSQ-138', title: 'Refactor du middleware d\'authentification',
      status: 'blocked', assigned_to: 'orion',
      created_at: ago(2 * H + 20 * M), updated_at: ago(9 * M),
      body: 'Extraire la logique de session dans un module dédié. Supprimer les dépendances circulaires.',
      labels: ['backend', 'refactor'], priority: 'medium',
      history: [
        { t: ago(2 * H + 20 * M), who: 'eric', text: 'Ticket créé.' },
        { t: ago(2 * H + 12 * M), who: 'orion', text: 'Statut → En cours.' },
        { t: ago(9 * M), who: 'orion', text: 'Statut → Bloqué. Erreur de typage non résolue.' },
      ],
      comments: [
        { t: ago(9 * M), who: 'orion', agent: true, text: 'Build cassé sur session.ts:88. Le type `LegacyToken` n\'est plus exporté.' },
      ],
    },
    {
      id: 'CSQ-145', title: 'Couvrir le tunnel de paiement en tests E2E',
      status: 'in-progress', assigned_to: 'nova',
      created_at: ago(20 * M), updated_at: ago(3 * S),
      body: 'Ajouter une suite Playwright couvrant le parcours panier → paiement → confirmation.',
      labels: ['tests', 'frontend'], priority: 'high',
      history: [
        { t: ago(20 * M), who: 'eric', text: 'Ticket créé et assigné à nova (claude).' },
        { t: ago(17 * M), who: 'nova', text: 'Statut → En cours.' },
      ],
      comments: [],
    },
    {
      id: 'CSQ-141', title: 'Documenter les webhooks sortants',
      status: 'in-progress', assigned_to: 'echo',
      created_at: ago(30 * M), updated_at: ago(8 * S),
      body: 'Rédiger docs/api/webhooks.md : événements, payloads, signatures, politique de retries.',
      labels: ['docs'], priority: 'low',
      history: [
        { t: ago(30 * M), who: 'eric', text: 'Ticket créé.' },
        { t: ago(24 * M), who: 'echo', text: 'Statut → En cours.' },
      ],
      comments: [],
    },
    {
      id: 'CSQ-140', title: 'Auditer les usages de legacy_token',
      status: 'open', assigned_to: null,
      created_at: ago(1 * H), updated_at: ago(1 * H),
      body: 'Recenser tous les usages de `legacy_token` dans le code et préparer un plan de retrait.',
      labels: ['tech-debt'], priority: 'medium',
      history: [ { t: ago(1 * H), who: 'eric', text: 'Ticket créé.' } ],
      comments: [],
    },
    {
      id: 'CSQ-139', title: 'Limiter le débit de l\'API publique',
      status: 'open', assigned_to: null,
      created_at: ago(1 * H + 40 * M), updated_at: ago(1 * H + 40 * M),
      body: 'Ajouter un rate-limit par clé d\'API (100 req/min). Réponse 429 normalisée.',
      labels: ['backend', 'sécurité'], priority: 'medium',
      history: [ { t: ago(1 * H + 40 * M), who: 'eric', text: 'Ticket créé.' } ],
      comments: [],
    },
    {
      id: 'CSQ-137', title: 'Page de statut publique',
      status: 'open', assigned_to: null,
      created_at: ago(3 * H), updated_at: ago(3 * H),
      body: 'Exposer une page de statut avec l\'uptime des services principaux.',
      labels: ['frontend'], priority: 'low',
      history: [ { t: ago(3 * H), who: 'eric', text: 'Ticket créé.' } ],
      comments: [],
    },
    {
      id: 'CSQ-133', title: 'Normaliser les réponses d\'erreur',
      status: 'done', assigned_to: 'rhea',
      created_at: ago(4 * H), updated_at: ago(31 * M),
      body: 'Unifier le format des erreurs API : { code, message, details }.',
      labels: ['backend'], priority: 'medium',
      history: [
        { t: ago(4 * H), who: 'eric', text: 'Ticket créé.' },
        { t: ago(3 * H), who: 'rhea', text: 'Statut → En cours.' },
        { t: ago(31 * M), who: 'rhea', text: 'Statut → Terminé. PR prête à relire.' },
      ],
      comments: [],
    },
    {
      id: 'CSQ-129', title: 'Migration des comptes inactifs',
      status: 'blocked', assigned_to: 'kilo',
      created_at: ago(6 * H), updated_at: ago(1 * H + 14 * M),
      body: 'Archiver les comptes sans activité depuis 18 mois.',
      labels: ['migration', 'data'], priority: 'low',
      history: [
        { t: ago(6 * H), who: 'eric', text: 'Ticket créé.' },
        { t: ago(5 * H), who: 'kilo', text: 'Statut → En cours.' },
        { t: ago(1 * H + 14 * M), who: 'kilo', text: 'Worker sorti (code 1). Ticket bloqué.' },
      ],
      comments: [],
    },
    {
      id: 'CSQ-128', title: 'Cache des requêtes de profil',
      status: 'done', assigned_to: 'rhea',
      created_at: ago(8 * H), updated_at: ago(5 * H),
      body: 'Mettre en cache les lectures de profil (TTL 5 min).',
      labels: ['perf'], priority: 'low',
      history: [
        { t: ago(8 * H), who: 'eric', text: 'Ticket créé.' },
        { t: ago(5 * H), who: 'rhea', text: 'Statut → Terminé.' },
      ],
      comments: [],
    },
  ];

  // ── Log seeds + generators ────────────────────────────────
  const K = { ts: 'term-ts', info: 'term-info', cmd: 'term-cmd', ok: 'term-ok', warn: 'term-warn', err: 'term-err', dim: 'term-dim' };
  function ts(d) {
    const x = d || new Date();
    return x.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  }

  const LOG_SEEDS = {
    'nova@checkout-revamp': [
      ['cmd', '$ npx playwright test checkout.e2e.ts'],
      ['dim', 'Using config from playwright.config.ts'],
      ['info', 'Running 18 tests using 4 workers'],
      ['ok', '  ✓ panier: ajoute un article (1.2s)'],
      ['ok', '  ✓ panier: met à jour la quantité (0.9s)'],
      ['ok', '  ✓ paiement: carte valide (2.1s)'],
      ['warn', '  ⚠ paiement: 3DS challenge — retry once'],
      ['ok', '  ✓ paiement: 3DS challenge (3.4s)'],
      ['info', '  … 12/18 passed'],
    ],
    'orion@checkout-revamp': [
      ['cmd', '$ npm run build'],
      ['info', '> tsc -p tsconfig.json'],
      ['err', 'src/auth/session.ts:88:14 - error TS2305:'],
      ['err', "  Module '\"./tokens\"' has no exported member 'LegacyToken'."],
      ['dim', '88   const t: LegacyToken = decode(raw)'],
      ['err', 'Found 1 error. Build failed.'],
      ['warn', '⏸  Worker bloqué — intervention requise.'],
    ],
    'atlas@checkout-revamp': [
      ['info', 'Analyse du schéma `sessions`…'],
      ['ok', '  ✓ schéma v1 détecté (3 colonnes token)'],
      ['info', 'Plan: ajouter token_v2, backfill, déprécier token_v1'],
      ['warn', '⏸  Question à l\'orchestrateur :'],
      ['dim', '   Migrer les enregistrements existants, ou seulement les futurs ?'],
    ],
    'rhea@checkout-revamp': [
      ['ok', '  ✓ format d\'erreur unifié sur 4 fichiers'],
      ['cmd', '$ npm test'],
      ['ok', '  ✓ 42 passing'],
      ['ok', '✅ Tâche terminée. PR prête.'],
    ],
    'vega@webhooks-v2': [
      ['cmd', '$ grep -rn "legacy_token" src/'],
      ['info', '23 occurrences dans 11 fichiers'],
      ['dim', 'src/auth/session.ts:88'],
      ['dim', 'src/api/middleware.ts:42'],
      ['info', 'Cartographie des usages en cours…'],
    ],
    'echo@webhooks-v2': [
      ['dim', 'Edit docs/api/webhooks.md'],
      ['ok', '  ✓ section "événements" rédigée'],
      ['ok', '  ✓ section "signatures" rédigée'],
      ['info', 'Rédaction de la section "retries"…'],
    ],
    'kilo@webhooks-v2': [
      ['info', 'En attente d\'une tâche assignée.'],
      ['dim', 'Aucune tâche in_progress pour ce teammate.'],
    ],
  };

  function seedLogs(worker) {
    const base = LOG_SEEDS[worker.id] || [['info', 'Session initialisée.']];
    let t = worker.created_at.getTime();
    return base.map((l, i) => {
      t += 1400 + i * 900;
      return { id: worker.id + '_l' + i, time: new Date(Math.min(t, now)), kind: l[0], text: l[1] };
    });
  }

  // streaming line pools for running workers
  const STREAM = {
    'nova@checkout-revamp': [
      ['ok', '  ✓ paiement: code promo (1.1s)'],
      ['ok', '  ✓ paiement: échec carte refusée (1.7s)'],
      ['info', '  … 14/18 passed'],
      ['ok', '  ✓ confirmation: email envoyé (0.8s)'],
      ['ok', '  ✓ confirmation: facture PDF (1.3s)'],
    ],
    'vega@webhooks-v2': [
      ['dim', 'src/api/middleware.ts:42'],
      ['dim', 'src/jobs/cleanup.ts:17'],
      ['info', 'Regroupement par module…'],
      ['ok', '  ✓ rapport d\'usage généré'],
    ],
    'echo@webhooks-v2': [
      ['info', '  rédaction du tableau de codes de retry…'],
      ['ok', '  ✓ exemple curl ajouté'],
      ['ok', '  ✓ section "retries" terminée'],
      ['info', 'Relecture orthographique…'],
    ],
  };

  let streamIdx = {};
  function nextStreamLine(worker) {
    const pool = STREAM[worker.id];
    if (!pool) {
      return { kind: 'dim', text: '  … traitement en cours' };
    }
    const i = (streamIdx[worker.id] || 0) % pool.length;
    streamIdx[worker.id] = i + 1;
    const l = pool[i];
    return { kind: l[0], text: l[1] };
  }

  // ── Relative time ─────────────────────────────────────────
  function fmtRel(date) {
    const diff = Math.max(0, Date.now() - new Date(date).getTime());
    const s = Math.floor(diff / 1000);
    if (s < 5) return 'à l\'instant';
    if (s < 60) return 'il y a ' + s + ' s';
    const m = Math.floor(s / 60);
    if (m < 60) return 'il y a ' + m + ' min';
    const h = Math.floor(m / 60);
    if (h < 24) return 'il y a ' + h + ' h';
    return 'il y a ' + Math.floor(h / 24) + ' j';
  }
  function fmtClock(date) {
    return new Date(date).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
  }
  function fmtDuration(from, to) {
    const diff = Math.max(0, (to ? new Date(to) : new Date()).getTime() - new Date(from).getTime());
    const m = Math.floor(diff / 60000);
    if (m < 60) return m + ' min';
    const h = Math.floor(m / 60);
    return h + ' h ' + (m % 60) + ' min';
  }

  window.CSQ = {
    workers, tickets, WORKER_STATUS, TICKET_STATUS, AGENTS,
    seedLogs, nextStreamLine, fmtRel, fmtClock, fmtDuration, ts, now,
  };
})();
