const DATA_VERSION = "20240507b";

async function loadFAQ() {
  try {
    console.log("Ask CielNet FAQ :: rendu structuré activé");
    const res = await fetch(`../data/cielnet_faq.json?v=${DATA_VERSION}`);
    const data = await res.json();
    const faq = data.entries;

    const container = document.getElementById("results");
    const search = document.getElementById("search");

    function render(filter = "") {
      container.innerHTML = "";

      const normalizedFilter = filter.trim().toLowerCase();
      const filtered = faq.filter(item => {
        if (!normalizedFilter) return true;

        const bits = [
          item.question,
          item.answer,
          item.section,
          item.tags ? item.tags.join(" ") : "",
          item.examples ? item.examples.join(" ") : "",
          item.follow_up,
          item.search_synonyms ? item.search_synonyms.join(" ") : ""
        ];

        const haystack = bits
          .filter(Boolean)
          .join(" ")
          .toLowerCase();

        return haystack.includes(normalizedFilter);
      });

      if (filtered.length === 0) {
        container.innerHTML = `
          <div class="empty-state">
            <p>🕵️‍♂️ Aucun résultat trouvé</p>
            <p class="hint">Essayez un autre mot-clé ou explorez les domaines ci-dessous.</p>
          </div>
        `;
        return;
      }

      const grouped = groupByDomain(filtered);
      grouped.forEach(({ domain, total, subsections }) => {
        container.appendChild(renderDomain(domain, total, subsections));
      });
    }

    search.addEventListener("input", e => render(e.target.value));
    render();
  } catch (err) {
    console.error(err);
    document.getElementById("results").innerHTML =
      "<p>❌ Impossible de charger le fichier de FAQ. Vérifie le chemin ou le JSON.</p>";
  }
}

function groupByDomain(entries) {
  const domainMap = new Map();

  entries.forEach(item => {
    const { domain, subsection } = parseSection(item.section);
    const domainKey = domain || "Divers";
    const subsectionKey = subsection || "Général";

    if (!domainMap.has(domainKey)) {
      domainMap.set(domainKey, new Map());
    }

    const subsectionMap = domainMap.get(domainKey);

    if (!subsectionMap.has(subsectionKey)) {
      subsectionMap.set(subsectionKey, []);
    }

    subsectionMap.get(subsectionKey).push(item);
  });

  return Array.from(domainMap.entries())
    .sort(([a], [b]) => a.localeCompare(b, "fr", { sensitivity: "base" }))
    .map(([domain, subsectionMap]) => {
      const subsections = Array.from(subsectionMap.entries())
        .sort(([a], [b]) => a.localeCompare(b, "fr", { sensitivity: "base" }))
        .map(([name, items]) => ({
          name,
          items: items.sort((a, b) => a.question.localeCompare(b.question, "fr"))
        }));

      const total = subsections.reduce((sum, sub) => sum + sub.items.length, 0);

      return { domain, total, subsections };
    });
}

function parseSection(section = "") {
  const trimmed = section.trim();
  if (!trimmed) return { domain: "Divers", subsection: "Général" };

  const doubleSpaceSplit = trimmed.split(/ {2,}/);
  if (doubleSpaceSplit.length > 1) {
    return {
      domain: capitalise(doubleSpaceSplit[0]),
      subsection: capitalise(doubleSpaceSplit.slice(1).join(" ").trim())
    };
  }

  const ampersandSplit = trimmed.split(/\s*&\s*/);
  if (ampersandSplit.length > 1) {
    return {
      domain: capitalise(ampersandSplit[0]),
      subsection: capitalise(ampersandSplit.slice(1).join(" & ").trim())
    };
  }

  const words = trimmed.split(/\s+/);
  if (words.length > 1) {
    return {
      domain: capitalise(words[0]),
      subsection: capitalise(trimmed.slice(words[0].length).trim())
    };
  }

  return { domain: capitalise(trimmed), subsection: "Général" };
}

function capitalise(str = "") {
  if (!str) return "";
  return str.charAt(0).toUpperCase() + str.slice(1);
}

function renderDomain(name, total, subsections) {
  const section = document.createElement("section");
  section.className = "domain";

  const header = document.createElement("header");
  header.className = "domain__header";
  header.innerHTML = `
    <h2>${name}</h2>
    <span class="domain__count">${total} ${total > 1 ? "entrées" : "entrée"}</span>
  `;

  section.appendChild(header);

  subsections.forEach(sub => {
    section.appendChild(renderSubsection(sub));
  });

  return section;
}

function renderSubsection({ name, items }) {
  const container = document.createElement("div");
  container.className = "subsection";

  const heading = document.createElement("h3");
  heading.textContent = name;

  const count = document.createElement("span");
  count.className = "subsection__count";
  count.textContent = `${items.length} ${items.length > 1 ? "fiches" : "fiche"}`;
  heading.appendChild(count);

  container.appendChild(heading);

  const list = document.createElement("div");
  list.className = "faq-grid";

  items.forEach(item => {
    list.appendChild(renderFAQCard(item));
  });

  container.appendChild(list);
  return container;
}

function renderFAQCard(item) {
  const card = document.createElement("article");
  card.className = "faq-card";

  const title = document.createElement("h4");
  title.textContent = item.question;

  const answer = document.createElement("div");
  answer.className = "faq-card__answer";
  formatAnswer(item).forEach(node => {
    answer.appendChild(node);
  });

  const meta = document.createElement("div");
  meta.className = "faq-card__meta";
  meta.appendChild(renderBadges(item));

  const extra = document.createElement("div");
  extra.className = "faq-card__extra";
  const hasExamples = appendList(extra, "Exemples", item.examples);
  const hasFollowUp = appendFollowUp(extra, item.follow_up);

  card.appendChild(title);
  card.appendChild(answer);
  card.appendChild(meta);
  if (hasExamples || hasFollowUp) {
    card.appendChild(extra);
  }

  return card;
}

function formatAnswer(item) {
  const sentences = splitSentences(item.answer);
  if (sentences.length === 0) {
    return [createParagraph(normaliseWhitespace(item.answer))];
  }

  const seed = hashString(`${item.id}-${item.section}`);
  const { domain } = parseSection(item.section);
  const voice = getVoiceProfile(domain);

  const reworked = sentences
    .map((sentence, index) => enrichSentence(sentence, index, seed, voice))
    .filter(Boolean);

  const grouped = groupSentences(reworked, seed, voice);
  const paragraphs = grouped.map(chunk => createParagraph(chunk.join(" ")));

  if (item.tags && item.tags.length) {
    const tagLead = pickVariant(seed + 5, voice.tagVariants || TAG_VARIANTS);
    paragraphs.push(createParagraph(`${tagLead} ${formatList(item.tags)}.`));
  }

  if (item.confidence) {
    const confidenceLine = buildConfidenceSentence(item.confidence, voice, seed + 6);
    if (confidenceLine) {
      paragraphs.push(createParagraph(confidenceLine));
    }
  }

  if (item.follow_up) {
    const followLead = pickVariant(seed + 7, voice.followVariants || FOLLOW_UP_VARIANTS);
    paragraphs.push(createParagraph(`${followLead} ${normaliseFollowUp(item.follow_up)}.`));
  } else if (shouldAddOutro(seed)) {
    const outro = pickVariant(seed + 8, voice.outros || OUTRO_VARIANTS);
    paragraphs.push(createParagraph(outro));
  }

  return paragraphs;
}

function renderBadges(item) {
  const badges = document.createElement("div");
  badges.className = "badge-row";

  if (item.confidence) {
    const confidence = document.createElement("span");
    confidence.className = `badge badge--${item.confidence}`;
    confidence.textContent = `Confiance : ${item.confidence}`;
    badges.appendChild(confidence);
  }

  (item.tags || []).forEach(tag => {
    const tagBadge = document.createElement("span");
    tagBadge.className = "badge";
    tagBadge.textContent = tag;
    badges.appendChild(tagBadge);
  });

  return badges;
}

function appendList(container, label, items) {
  if (!items || items.length === 0) return false;

  const block = document.createElement("div");
  block.className = "extra-block";

  const title = document.createElement("span");
  title.className = "extra-block__label";
  title.textContent = label;

  const list = document.createElement("ul");
  items.forEach(entry => {
    const li = document.createElement("li");
    li.textContent = entry;
    list.appendChild(li);
  });

  block.appendChild(title);
  block.appendChild(list);
  container.appendChild(block);
  return true;
}

function appendFollowUp(container, followUp) {
  if (!followUp) return false;

  const block = document.createElement("div");
  block.className = "extra-block";

  const title = document.createElement("span");
  title.className = "extra-block__label";
  title.textContent = "À suivre";

  const text = document.createElement("p");
  text.className = "extra-block__text";
  text.textContent = followUp;

  block.appendChild(title);
  block.appendChild(text);
  container.appendChild(block);
  return true;
}

loadFAQ();

const DEFAULT_PRIMARY_VARIANTS = [
  "Côté pratique,",
  "Dans les faits,",
  "Concrètement,",
  "Pour mémoire,",
  "Sur le terrain,",
  "À noter que",
  "Petit rappel :",
  "Côté sécurité,",
  "Côté opérationnel,",
  "En interne,"
];

const DEFAULT_SECONDARY_VARIANTS = [
  "Autre point utile :",
  "On ajoute souvent que",
  "À cela s'ajoute que",
  "Côté support,",
  "En parallèle,",
  "Les équipes mentionnent aussi que",
  "L'IA rappelle régulièrement que",
  "Et pour finir,",
  "Enfin,",
  "Dernier détail :"
];

const TAG_VARIANTS = [
  "Côté mots-clés, on parle souvent de",
  "Les thématiques associées tournent autour de",
  "On classe généralement cette fiche dans",
  "En interne, on tague le sujet avec",
  "Pour les recherches, on retient surtout",
  "Les catégories utiles :"
];

const FOLLOW_UP_VARIANTS = [
  "Pour aller plus loin, on enchaîne avec",
  "Si une nouvelle question apparaît, on consulte",
  "En cas de doute, on se réfère à",
  "S'il faut prolonger la discussion, la fiche suivante est",
  "Besoin d'un complément ? On regarde",
  "Pour la suite, on garde sous la main"
];

const OUTRO_VARIANTS = [
  "Bref, ce cadre évite pas mal de surprises au quotidien.",
  "En résumé, cette routine garde l'équipe sereine.",
  "On s'y tient parce que c'est ce qui fonctionne le mieux pour CielNet.",
  "Au final, c'est ce mix qui nous garde rapides et fiables.",
  "Résultat : moins d'improvisation et plus de sérénité dans l'équipe.",
  "Conclusion partagée : ça nous fait gagner du temps et de l'énergie."
];

function splitSentences(answer = "") {
  if (!answer) return [];

  let working = answer.replace(/\r\n?/g, " ");
  const stash = [];

  const protect = regex => {
    working = working.replace(regex, match => {
      const token = `§${stash.length}§`;
      stash.push({ token, value: match });
      return token;
    });
  };

  protect(/prenom\.nom/gi);
  protect(/backup\.cielnet/gi);
  protect(/\d+\.\d+/g);

  working = working.replace(/\s+/g, " ").trim();

  const primarySplit = working.length
    ? working.split(/(?<=[.!?])\s+/).filter(Boolean)
    : [];

  const sentences = (primarySplit.length ? primarySplit : [working])
    .flatMap(part => part.split(/(?<=;)\s+(?=[A-ZÀ-ÿ0-9#])/))
    .map(part => {
      let restored = part;
      stash.forEach(({ token, value }) => {
        restored = restored.split(token).join(value);
      });
      return restored.replace(/\s+/g, " ").trim();
    })
    .filter(part => part && !/^[()]+$/.test(part));

  return sentences;
}

function capitaliseSentence(sentence = "") {
  if (!sentence) return "";
  const trimmed = sentence.trim();
  const first = trimmed.charAt(0).toUpperCase() + trimmed.slice(1);
  return /[.!?]$/.test(first) ? first : `${first}.`;
}

function createParagraph(text) {
  const paragraph = document.createElement("p");
  paragraph.textContent = text;
  return paragraph;
}

function normaliseWhitespace(text = "") {
  return text.replace(/\s+/g, " ").trim();
}

function enrichSentence(sentence, index, seed, voice) {
  const polished = beautifyClause(sentence);
  if (!polished) return "";

  if (index === 0) {
    return ensureEnding(polished);
  }

  const prefixes =
    index === 1 ? voice.primary || DEFAULT_PRIMARY_VARIANTS : voice.secondary || DEFAULT_SECONDARY_VARIANTS;
  const prefix = pickVariant(seed + index, prefixes);

  const withoutPunctuation = polished.replace(/[.!?]+$/u, "");
  const lowered = lowercaseFirst(withoutPunctuation);
  const combined = prefix ? `${prefix} ${lowered}` : withoutPunctuation;

  return ensureEnding(capitaliseSentence(combined));
}

function tidySentence(sentence = "") {
  return normaliseWhitespace(
    sentence
      .replace(/\s*:\s*/g, " : ")
      .replace(/\s*;\s*/g, "; ")
      .replace(/\s*\(\s*/g, " (")
      .replace(/\s*\)\s*/g, ") ")
  );
}

function beautifyClause(clause = "") {
  const cleaned = tidySentence(clause);
  if (!cleaned) return "";

  let text = expandAbbreviations(cleaned)
    .replace(/\s*\+\s*/g, ", ")
    .replace(/\s*\/\s*/g, " ou ")
    .replace(/\s*=\s*/g, " = ")
    .replace(/\s*-\s*/g, "-")
    .replace(/\s{2,}/g, " ")
    .trim();

  if (!text) return "";

  if (text.includes("(") && !text.includes(")")) {
    text += ")";
  }

  if (text.match(/,\s*$/)) {
    text = text.replace(/,\s*$/, "");
  }

  text = text.replace(/\bVitez\b/gi, "Évitez");

  text = text.replace(/^IA\b/gi, "L'IA");
  text = text.replace(/([\s(])IA\b/gi, (_, prefix) => `${prefix}l'IA`);
  text = text.replace(/\b(notre|votre|leur|son|sa)\s+l'IA\b/gi, (_, pronoun) => `${pronoun} IA`);

  const trimmed = text.replace(/[.!?;:,]+$/u, "");
  const startsWithDigit = /^\d/.test(trimmed);
  const commaCount = (trimmed.match(/,/g) || []).length;
  const looksLikeList = commaCount >= 2 || /[#;]/.test(trimmed);
  const lacksVerb = !HAS_VERB_REGEX.test(trimmed);
  const lowerTrimmed = trimmed.toLowerCase();
  const softStart = SOFT_STARTS.some(prefix => lowerTrimmed.startsWith(prefix));
  const needsStructure =
    (!softStart && lacksVerb) ||
    !SENTENCE_START_REGEX.test(trimmed) ||
    trimmed.includes(":") ||
    looksLikeList ||
    startsWithDigit;
  if (needsStructure) {
    const structured = buildStructuredSentence(trimmed);
    if (structured) {
      return ensureEnding(structured);
    }
  }

  if (!SENTENCE_START_REGEX.test(trimmed)) {
    if (startsWithDigit) {
      text = `On compte ${lowercaseFirst(trimmed)}`;
    } else if (looksLikeList) {
      text = `On retrouve : ${trimmed}`;
    } else {
      text = `On précise que ${lowercaseFirst(trimmed)}`;
    }
  } else {
    text = trimmed;
  }

  return ensureEnding(text);
}

const SPECIFIC_REWRITES = [
  {
    test: /^Compte créé J-1 par l'IA$/i,
    rewrite: () => "Le compte est créé la veille (J-1) par l'IA."
  },
  {
    test: /^Login prenom\.nom, mot de passe temporaire sms$/i,
    rewrite: () => "Le login suit le format prenom.nom et un mot de passe temporaire est envoyé par SMS."
  },
  {
    test: /^Première connexion it obligatoire pour double authentification$/i,
    rewrite: () => "La première connexion avec l'équipe IT est obligatoire pour activer la double authentification."
  },
  {
    test: /^Accès progressifs : basic j1, dev j3, admin j15$/i,
    rewrite: () =>
      "Les accès sont progressifs : niveau basic au jour J1, accès développeur au jour J3 et accès administrateur au jour J15."
  }
];

const SOFT_STARTS = ["bienvenue", "merci", "attention", "chut", "fun fact"];
const PROPER_NOUNS = new Set([
  "CielNet",
  "CielConnect",
  "CielCantine",
  "CielAuth",
  "CielMeet",
  "CielWork",
  "VacanceNet",
  "Slack",
  "GitLab",
  "GitHub",
  "Prometheus",
  "Grafana",
  "Terraform",
  "Vault",
  "Docker",
  "PostgreSQL"
]);

const ABBREVIATION_PATTERNS = [
  { pattern: /\bMDP\b/gi, replacement: "mot de passe" },
  { pattern: /\bMFA\b/gi, replacement: "double authentification" },
  { pattern: /\bTR\b(?![a-z])/gi, replacement: "titres-restaurant" },
  { pattern: /\bRTT\b/gi, replacement: "jours de RTT" },
  { pattern: /\bCPF\b/gi, replacement: "CPF" },
  { pattern: /\bRBAC\b/gi, replacement: "RBAC" },
  { pattern: /\bBYOD\b/gi, replacement: "BYOD" },
  { pattern: /\bPKI\b/gi, replacement: "PKI" },
  { pattern: /\bSSO\b/gi, replacement: "SSO" },
  { pattern: /\bVPN\b/gi, replacement: "VPN" },
  { pattern: /\bSLA\b/gi, replacement: "SLA" },
  { pattern: /\bKPI\b/gi, replacement: "KPI" },
  { pattern: /\bOKR\b/gi, replacement: "OKR" },
  { pattern: /\bAPI\b/gi, replacement: "API" },
  { pattern: /\bIT\b/gi, replacement: "IT" }
];

function expandAbbreviations(text) {
  return ABBREVIATION_PATTERNS.reduce(
    (acc, { pattern, replacement }) => acc.replace(pattern, replacement),
    text
  );
}

function buildStructuredSentence(text) {
  const rewritten = applySpecificRewrite(text);
  if (rewritten) {
    return rewritten;
  }

  const colonIndex = text.indexOf(":");
  if (colonIndex > -1 && colonIndex < text.length - 1) {
    const head = text.slice(0, colonIndex).trim();
    const tail = text.slice(colonIndex + 1).trim();
    const headSentence = buildSubjectSentence(head);
    const tailSentence = formatEnumeration(tail, { leadingConjunction: true });
    return `${headSentence} ${tailSentence}`;
  }

  return buildSubjectSentence(text);
}

function applySpecificRewrite(text) {
  const entry = SPECIFIC_REWRITES.find(rule => rule.test.test(text));
  return entry ? entry.rewrite(text) : null;
}

const SUBJECT_RULES = {
  compte: rest => `Le compte ${ensureVerb(rest, { subjectLower: "compte", defaultVerb: "est" })}`,
  login: rest => {
    let formatted = rest
      .replace(/, mot de passe temporaire sms/i, " et un mot de passe temporaire est envoyé par SMS")
      .replace(/prenom\.nom/gi, "prenom.nom");
    return `Le login suit le format ${formatted}`;
  },
  première: rest => `La première ${ensureVerb(rest, { subjectLower: "première", defaultVerb: "est" })}`,
  accès: rest => {
    const formatted = rest.replace(
      /basic j1, dev j3, admin j15/gi,
      "basic au jour J1, développeur au jour J3 et administrateur au jour J15"
    );
    return `Les accès ${ensureVerb(formatted, { subjectLower: "accès", defaultVerb: "sont" })}`;
  },
  formation: rest => {
    const formatted = rest.replace(/sécurité obligatoire 48h/gi, "doit être suivie dans les 48 heures pour la sécurité");
    return `La formation ${ensureVerb(formatted, { subjectLower: "formation", defaultVerb: "est" })}`;
  },
  feedback: rest => `Le feedback ${ensureVerb(rest, { subjectLower: "feedback", defaultVerb: "s'organise" })}`,
  mutuelle: rest => `La mutuelle ${ensureVerb(rest, { subjectLower: "mutuelle", defaultVerb: "couvre" })}`,
  programme: rest => `Le programme ${ensureVerb(rest, { subjectLower: "programme", defaultVerb: "prévoit" })}`,
  vacancenet: rest => `VacanceNet ${ensureVerb(rest, { subjectLower: "vacancenet", defaultVerb: "centralise" })}`,
  vendredi: rest => `Le vendredi ${ensureVerb(rest, { subjectLower: "vendredi", defaultVerb: "reste" })}`,
  jeudi: rest => `Le jeudi ${ensureVerb(rest, { subjectLower: "jeudi", defaultVerb: "propose" })}`,
  slack: rest => `Slack ${ensureVerb(rest, { subjectLower: "slack", defaultVerb: "complète" })}`,
  "#random": rest => `Le canal #random ${ensureVerb(rest, { subjectLower: "#random", defaultVerb: "héberge" })}`,
  afterwork: rest => `L'afterwork ${ensureVerb(rest, { subjectLower: "afterwork", defaultVerb: "est" })}`,
  parcours: rest => {
    const formatted = rest.replace(/\s*\(\s*/g, " (").replace(/\s*\)\s*/g, ")");
    return `Le parcours ${ensureVerb(formatted, { subjectLower: "parcours", defaultVerb: "prévoit" })}`;
  }
};

function buildSubjectSentence(segment) {
  const match = segment.match(/^([A-Za-zÀ-ÿ#0-9-]+)(.*)$/u);
  if (!match) return capitaliseSentence(segment);
  const [, word, rawRest] = match;
  const rest = rawRest.trim();
  const lower = word.toLowerCase();

  if (SUBJECT_RULES[lower]) {
    return SUBJECT_RULES[lower](rest);
  }

  const subjectInfo = guessSubject(lower, word);
  const predicate = ensureVerb(rest, subjectInfo);
  return predicate ? `${subjectInfo.subject} ${predicate}` : subjectInfo.subject;
}

function guessSubject(lower, original) {
  if (SUBJECT_RULES[lower]) {
    return { subject: SUBJECT_RULES[lower](""), defaultVerb: "est", subjectLower: lower };
  }

  if (lower.startsWith("ciel")) {
    return { subject: original, defaultVerb: "propose", subjectLower: lower };
  }

  if (lower === "ia") {
    return { subject: "L'IA", defaultVerb: "analyse", subjectLower: lower };
  }

  if (lower.startsWith("#")) {
    return { subject: `Le canal ${original}`, defaultVerb: "regroupe", subjectLower: lower };
  }

  if (/^\d/.test(lower)) {
    return { subject: `Le repère ${original}`, defaultVerb: "est", subjectLower: lower };
  }

  if (original === original.toUpperCase() && original.length <= 4) {
    return { subject: original, defaultVerb: "est", subjectLower: lower };
  }

  if (lower.endsWith("s")) {
    return { subject: `Les ${original.toLowerCase()}`, defaultVerb: "sont", subjectLower: lower };
  }

  if (/^[aeiouyh]/i.test(lower)) {
    return { subject: `L'${original.toLowerCase()}`, defaultVerb: "est", subjectLower: lower };
  }

  if (lower.endsWith("e")) {
    return { subject: `La ${original.toLowerCase()}`, defaultVerb: "est", subjectLower: lower };
  }

  return { subject: `Le ${original.toLowerCase()}`, defaultVerb: "est", subjectLower: lower };
}

function ensureVerb(rest, { subjectLower = "", defaultVerb = "est" } = {}) {
  const text = rest.trim();
  if (!text) return "";

  if (
    /^(est|sont|doit|doivent|permet|permettent|garantit|garantissent|offre|offrent|assure|assurent|prévoit|prévoient|organise|organisent|couvre|couvrent|fonctionne|fonctionnent|autorise|autorisent|garde|gèrent|met|prépare|rappelle|décrit|propose|passe|impose|recommande|déploie|détaille|accompagne)/i.test(
      text
    )
  ) {
    return text;
  }

  if (/^:/.test(text)) {
    return text;
  }

  if (/^\d/.test(text)) {
    return `est fixé à ${text}`;
  }

  if (/^(créé|assigné|attribué|déployé|prévu|fourni|organisé|géré|monitoré|activé|ouvert|enregistré|mesuré|préparé)/i.test(text)) {
    return `est ${text}`;
  }

  if (/^(disponibles|ouverts|fournis|organisés|préparés|gérés|partagés)/i.test(text)) {
    return `sont ${text}`;
  }

  if (subjectLower === "accès") {
    return `sont ${text}`;
  }

  if (subjectLower === "login") {
    return `suit ${text}`;
  }

  return `${defaultVerb} ${text}`;
}

function formatEnumeration(text, options = {}) {
  if (!text) return "";
  const fragments = text
    .split(/\s*,\s*/)
    .map(item => item.trim())
    .filter(Boolean);

  if (fragments.length <= 1) {
    const single = transformListItem(fragments[0] || text);
    return options.leadingConjunction ? prependQue(single) : single;
  }

  const transformed = fragments.map(transformListItem);
  if (options.leadingConjunction) {
    for (let i = 0; i < transformed.length; i += 1) {
      transformed[i] = prependQue(transformed[i]);
    }
  }

  const last = transformed.pop();
  const joined = `${transformed.join(", ")} et ${last}`;
  return joined;
}

function transformListItem(item = "") {
  const lower = item.toLowerCase();

  if (lower.startsWith("buddy")) {
    return "un buddy est assigné";
  }

  if (lower.startsWith("café rh")) {
    return "un café RH de bienvenue est prévu";
  }

  if (lower.startsWith("kit de bienvenue")) {
    return "un kit de bienvenue (badge, laptop, guide) est remis";
  }

  if (lower.startsWith("micro-ondes")) {
    return "des micro-ondes sont disponibles";
  }

  if (lower.startsWith("distributeurs")) {
    return "des distributeurs healthy sont accessibles";
  }

  if (lower.startsWith("café premium")) {
    return "un café premium est servi";
  }

  if (lower.startsWith("#")) {
    return `le canal ${item}`;
  }

  return item;
}

function prependQue(phrase = "") {
  const trimmed = phrase.trim();
  if (!trimmed) return "";
  const startsWithVowel = /^[aeiouh]/i.test(trimmed);
  const prefix = startsWithVowel ? "qu'" : "que ";
  return `${prefix}${trimmed}`;
}

const SENTENCE_START_REGEX =
  /^["'“”‘’]?(?:[A-ZÀ-Ÿ0-9]|L'|Le |La |Les |Un |Une |Des |Dans |Pour |Pendant |Grâce |Lorsque |En cas |En |Si |Après |Avec |Selon |Best |Ciel|VacanceNet|Programme|Ce |Cette |Ces |Tous |Toutes |Chaque |On |Nous |Il |Elle |Ils |Elles|Au |Aux |À |Sur |Sous |Dès )/u;
const HAS_VERB_REGEX =
  /\b(est|sont|doit|doivent|permet|permettent|garantit|garantissent|offre|offrent|assure|assurent|prévoit|prévoient|organise|organisent|couvre|couvrent|fonctionne|fonctionnent|autorise|autorisent|garde|gèrent|analyse|déploie|propose|dispose|prépare|réalise|assigne|surveille|prend|comprend|collecte|met|partage|coordonne|implique)/i;

function lowercaseFirst(text = "") {
  const match = text.match(/^["'“”‘’]*([A-Za-zÀ-ÿ]+)/u);
  if (match) {
    const word = match[1];
    const isProper =
      PROPER_NOUNS.has(word) || (word[0] === word[0].toUpperCase() && /[A-Z]/.test(word.slice(1)));
    if (isProper) {
      return text;
    }
  }

  return text.replace(/^(["'“”‘’]*)([A-ZÀ-Ÿ])/u, (_, prefix, letter) => `${prefix}${letter.toLowerCase()}`);
}

function ensureEnding(text = "") {
  const trimmed = text.trim();
  if (!trimmed) return "";
  return /[.!?)]$/.test(trimmed) ? trimmed : `${trimmed}.`;
}

function groupSentences(sentences, seed, voice) {
  const groups = [];
  let cursor = 0;
  const chunkSizes = voice.chunkSizes && voice.chunkSizes.length ? voice.chunkSizes : [2, 3];

  while (cursor < sentences.length) {
    const remaining = sentences.length - cursor;
    if (remaining === 1) {
      groups.push([sentences[cursor]]);
      break;
    }

    const index = (seed + cursor) % chunkSizes.length;
    const rawSize = chunkSizes[index];
    const size = Math.min(rawSize, remaining);
    groups.push(sentences.slice(cursor, cursor + size));
    cursor += size;
  }

  return groups;
}

function hashString(str = "") {
  let hash = 0;
  for (let i = 0; i < str.length; i += 1) {
    hash = (hash << 5) - hash + str.charCodeAt(i);
    hash |= 0;
  }
  return Math.abs(hash);
}

function pickVariant(seed, variants) {
  if (!variants.length) return "";
  return variants[seed % variants.length];
}

function getVoiceProfile(domain = "") {
  const key = inferDomainKey(domain);
  return VOICE_PROFILES[key] || DEFAULT_VOICE_PROFILE;
}

function inferDomainKey(domain = "") {
  const upper = domain.toUpperCase();
  if (upper.startsWith("RH")) return "RH";
  if (upper.startsWith("IT")) return "IT";
  if (upper.startsWith("SUPPORT")) return "SUPPORT";
  if (upper.startsWith("OPÉRATIONS") || upper.startsWith("OPERATIONS")) return "OPS";
  if (upper.startsWith("SÉCURITÉ") || upper.startsWith("SECURITE")) return "SECURITY";
  if (upper.startsWith("DATA")) return "DATA";
  if (upper.startsWith("SCÉNARIOS") || upper.startsWith("SCENARIOS")) return "SCENARIOS";
  if (upper.startsWith("EASTER")) return "LORE";
  if (upper.startsWith("JURIDIQUE")) return "LEGAL";
  return "DEFAULT";
}

const DEFAULT_VOICE_PROFILE = {
  primary: DEFAULT_PRIMARY_VARIANTS,
  secondary: DEFAULT_SECONDARY_VARIANTS,
  tagVariants: TAG_VARIANTS,
  followVariants: FOLLOW_UP_VARIANTS,
  outros: OUTRO_VARIANTS,
  chunkSizes: [2, 2, 3]
};

const VOICE_PROFILES = {
  RH: {
    primary: [
      "Dans la vie d'équipe,",
      "Côté accompagnement,",
      "Pour le quotidien RH,",
      "Sur l'expérience collaborateur,",
      "En pratique côté people,"
    ],
    secondary: [
      "Les collègues ajoutent souvent que",
      "Les coachs rappellent aussi que",
      "On profite pour rappeler que",
      "Le collectif souligne que",
      "On glisse également que"
    ],
    outros: [
      "Bref, on veille à ce que chacun se sente accueilli sans perdre de temps.",
      "Au final, l'objectif reste de rendre le parcours collaborateur fluide et humain.",
      "Résultat : on garde une ambiance chaleureuse tout en restant carré sur l'orga."
    ],
    chunkSizes: [2, 3, 3]
  },
  IT: {
    primary: [
      "Côté technique,",
      "Sur l'aspect infra,",
      "Dans la pratique IT,",
      "Pour l'équipe tech,",
      "Version terrain côté support :"
    ],
    secondary: [
      "Les admins précisent aussi que",
      "Côté supervision, on insiste sur le fait que",
      "Les runbooks rappellent que",
      "Les SRE ajoutent souvent que",
      "L'automatisation note également que"
    ],
    tagVariants: [
      "Côté mots-clés techniques, on parle surtout de",
      "Les tags utilisés côté support :",
      "Pour filtrer dans le portail IT, cherche",
      "Dans nos runbooks, on classe ça sous"
    ],
    chunkSizes: [2, 2, 3]
  },
  SUPPORT: {
    primary: [
      "Vue service client,",
      "Dans la relation produit,",
      "Côté support,",
      "En front office,",
      "Au quotidien avec les utilisateurs,"
    ],
    secondary: [
      "Les expert·es produit complètent en disant que",
      "On observe aussi que",
      "Les feedbacks clients montrent que",
      "Sur le terrain, on précise également que",
      "Les CSM rappellent aussi que"
    ]
  },
  OPS: {
    primary: [
      "Côté opérations,",
      "Dans la salle de contrôle,",
      "Pour l'équipe DevOps,",
      "Au quotidien sur la production,",
      "Dans les rituels d'exploitation,"
    ],
    secondary: [
      "Les on-call précisent aussi que",
      "Les postmortems rappellent que",
      "Les dashboards exposent également que",
      "Les playbooks ajoutent que",
      "On garde en tête que"
    ],
    chunkSizes: [2, 3, 2]
  },
  SECURITY: {
    primary: [
      "Côté sécurité,",
      "Dans les politiques sécurité,",
      "Côté conformité,",
      "Dans les contrôles,",
      "Sur le volet sécurité,"
    ],
    secondary: [
      "Les analystes SOC précisent que",
      "Les audits rappellent aussi que",
      "Les alertes incluent souvent l'idée que",
      "Les contrôles annuels montrent que",
      "Notre CISO insiste sur le point suivant :"
    ],
    chunkSizes: [2, 2, 2]
  },
  DATA: {
    primary: [
      "Côté data,",
      "Dans l'équipe RAG,",
      "Pour les pipelines ML,",
      "Dans les labs data,",
      "Sur les stacks analytiques,"
    ],
    secondary: [
      "Les data engineers ajoutent que",
      "Les analystes notent aussi que",
      "Les retours du labo montrent que",
      "Les notebooks indiquent que",
      "On garde en note que"
    ]
  },
  SCENARIOS: {
    primary: [
      "En situation de démo,",
      "Dans nos scénarios,",
      "Version showtime,",
      "Pour les présentations clients,",
      "En mode storytelling,"
    ],
    secondary: [
      "Les démos live rappellent aussi que",
      "Les product specialists ajoutent que",
      "Les scripts d'animation mentionnent que",
      "Pour garder l'effet wahou, on précise que",
      "Les répétitions soulignent que"
    ],
    chunkSizes: [3, 2, 3]
  },
  LORE: {
    primary: [
      "Dans la légende CielNet,",
      "Côté folklore interne,",
      "Dans les couloirs on murmure que",
      "Version lore,",
      "Dans les easter eggs,"
    ],
    secondary: [
      "Les aficionados racontent aussi que",
      "Les archives officieuses indiquent que",
      "La tradition geek ajoute que",
      "Le canal #lore partage aussi que",
      "L'IA goguenarde précise que"
    ],
    outros: [
      "Bref, la légende continue de grandir à chaque commit.",
      "Conclusion : la folklore maison reste bien vivant.",
      "En résumé, c'est le lore qui rend CielNet tellement unique."
    ],
    chunkSizes: [2, 3, 2]
  },
  LEGAL: {
    primary: [
      "Côté juridique,",
      "Pour la conformité,",
      "Version conformité,",
      "Dans les chartes légales,",
      "Côté obligations,"
    ],
    secondary: [
      "Le service légal rappelle aussi que",
      "Les juristes notent que",
      "La conformité ajoute que",
      "Les audits rapportent que",
      "Les process RGPD soulignent que"
    ],
    chunkSizes: [2, 2, 2]
  }
};

const CONFIDENCE_VARIANTS = {
  high: [
    "Indice de confiance élevé : la procédure est revue chaque trimestre avec les référent·es.",
    "Fiabilité vérifiée : les équipes auditent ce processus à chaque onboarding.",
    "Confiance haute, validée par la dernière revue qualité."
  ],
  medium: [
    "Indice de confiance moyen : on reste attentifs aux retours terrain pour ajuster.",
    "Confiance intermédiaire, l'équipe améliore encore la documentation.",
    "Processus stabilisé mais encore perfectible d'après les dernières rétros."
  ],
  low: [
    "Confiance limitée : document en cours de mise à jour.",
    "Indice de confiance bas, à challenger avec votre manager.",
    "Fiabilité à confirmer : vérifiez les dernières communications internes."
  ]
};

function buildConfidenceSentence(confidence, voice, seed) {
  const key = confidence.toLowerCase();
  const variants = CONFIDENCE_VARIANTS[key];
  if (!variants || variants.length === 0) return "";
  return pickVariant(seed, variants);
}
function formatList(values) {
  if (values.length === 1) return values[0];
  const last = values[values.length - 1];
  return `${values.slice(0, -1).join(", ")} et ${last}`;
}

function normaliseFollowUp(text = "") {
  const stripped = text.trim().replace(/\?+$/, "");
  return stripped.charAt(0).toUpperCase() + stripped.slice(1);
}

function shouldAddOutro(seed) {
  return seed % 3 === 0;
}
