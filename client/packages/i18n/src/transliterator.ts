// Comprehensive English to Devanagari (Hindi / Marathi) Phonetic Transliterator

const INDEPENDENT_VOWELS: Record<string, string> = {
  aa: "आ",
  a: "अ",
  ii: "ई",
  ee: "ई",
  i: "इ",
  uu: "ऊ",
  oo: "ऊ",
  u: "उ",
  ai: "ऐ",
  au: "औ",
  ou: "औ",
  e: "ए",
  o: "ओ",
  ri: "ऋ",
  ru: "ऋ",
};

const VOWEL_MATRAS: Record<string, string> = {
  aa: "ा",
  a: "", // inherent 'a'
  ii: "ी",
  ee: "ी",
  i: "ि",
  uu: "ू",
  oo: "ू",
  u: "ु",
  ai: "ै",
  au: "ौ",
  ou: "ौ",
  e: "े",
  o: "ो",
  ri: "ृ",
  ru: "ृ",
};

// Multi-character consonant tokens sorted by length (longest match first)
const CONSONANTS: [string, string][] = [
  ["dny", "ज्ञ"],
  ["jny", "ज्ञ"],
  ["gya", "ज्ञा"],
  ["gy", "ज्ञ"],
  ["ksh", "क्ष"],
  ["shh", "ष"],
  ["chh", "छ"],
  ["shr", "श्र"],
  ["ch", "च"],
  ["kh", "ख"],
  ["gh", "घ"],
  ["jh", "झ"],
  ["th", "थ"],
  ["dh", "ध"],
  ["ph", "फ"],
  ["bh", "भ"],
  ["sh", "श"],
  ["tr", "त्र"],
  ["ng", "ङ"],
  ["ny", "ञ"],
  ["sk", "स्क"],
  ["st", "स्त"],
  ["sp", "स्प"],
  ["sm", "स्म"],
  ["sn", "स्न"],
  ["sw", "स्व"],
  ["sv", "स्व"],
  ["pr", "प्र"],
  ["br", "ब्र"],
  ["kr", "क्र"],
  ["gr", "ग्र"],
  ["dr", "द्र"],
  ["k", "क"],
  ["g", "ग"],
  ["c", "क"],
  ["j", "ज"],
  ["t", "त"],
  ["d", "द"],
  ["n", "न"],
  ["p", "प"],
  ["f", "फ"],
  ["b", "ब"],
  ["m", "म"],
  ["y", "य"],
  ["r", "र"],
  ["l", "ल"],
  ["v", "व"],
  ["w", "व"],
  ["s", "स"],
  ["h", "ह"],
  ["x", "क्स"],
  ["z", "ज़"],
  ["q", "क"],
];

// Common name dictionary for 100% natural, polished output of well-known names and terms
const COMMON_NAMES_MAP: Record<string, string> = {
  rakesh: "राकेश",
  lokesh: "लोकेश",
  aman: "अमन",
  arjun: "अर्जुन",
  suresh: "सुरेश",
  rohan: "रोहन",
  pooja: "पूजा",
  puja: "पूजा",
  sneha: "स्नेहा",
  anjali: "अंजली",
  vikas: "विकास",
  deepak: "दीपक",
  dipak: "दीपक",
  manish: "मनीष",
  gaurav: "गौरव",
  nikhil: "निखिल",
  priya: "प्रिया",
  sachin: "सचिन",
  kavita: "कविता",
  aditya: "आदित्य",
  aakash: "आकाश",
  akash: "आकाश",
  rahul: "राहुल",
  prashant: "प्रशांत",
  swapnil: "स्वप्निल",
  mahesh: "महेश",
  abhishek: "अभिषेक",
  kishor: "किशोर",
  kishore: "किशोर",
  santosh: "संतोष",
  ashok: "अशोक",
  vijay: "विजय",
  sanjay: "संजय",
  nitin: "नितिन",
  ajay: "अजय",
  sunil: "सुनील",
  anil: "अनिल",
  pankaj: "पंकज",
  dinesh: "दिनेश",
  rajesh: "राजेश",
  ramesh: "रमेश",
  neha: "नेहा",
  swati: "स्वाती",
  pratik: "प्रतीक",
  omkar: "ओमकार",
  shubham: "शुभम",
  akshay: "अक्षय",
  tanmay: "तन्मय",
  tejas: "तेजस",
  isawari: "ईश्वरी",
  ishwari: "ईश्वरी",
  sohanda: "सोहंदा",
  jagtap: "जगतप",
  patil: "पाटील",
  sharma: "शर्मा",
  verma: "वर्मा",
  gupta: "गुप्ता",
  deshmukh: "देशमुख",
  kulkarni: "कुलकर्णी",
  joshi: "जोशी",
  pawar: "पवार",
  more: "मोरे",
  jadhav: "जाधव",
  chavan: "चव्हाण",
  shinde: "शिंदे",
  gaikwad: "गायकवाड",
  bhosale: "भोसले",
  yadav: "यादव",
  singh: "सिंह",
  kumar: "कुमार",
  mishra: "मिश्रा",
  pandey: "पांडेय",
  tiwari: "तिवारी",
  dubey: "दुबे",
  thakur: "ठाकूर",
  shah: "शाह",
  mehta: "मेहता",
  patel: "पटेल",
  reddy: "रेड्डी",
  nair: "नायर",
  menon: "मेनन",
  iyer: "अय्यर",
  rao: "राव",
};

export function transliterateWordToDevanagari(rawWord: string): string {
  if (!rawWord) return "";
  const word = rawWord.trim().toLowerCase();
  if (!word) return rawWord;

  // Direct lookup in high-frequency name lexicon
  if (COMMON_NAMES_MAP[word]) {
    return COMMON_NAMES_MAP[word];
  }

  // Handle special characters or pure numbers
  if (!/^[a-z]+$/i.test(word)) {
    return rawWord;
  }

  let result = "";
  let i = 0;
  const n = word.length;

  while (i < n) {
    // 1. Check if at start or after vowel/independent position
    if (i === 0) {
      // Check for leading independent vowel
      let matchedVowel = "";
      for (const v of ["aa", "ii", "ee", "uu", "oo", "ai", "au", "ou", "ri", "ru", "a", "i", "u", "e", "o"]) {
        if (word.startsWith(v, i)) {
          matchedVowel = v;
          break;
        }
      }
      if (matchedVowel) {
        result += INDEPENDENT_VOWELS[matchedVowel] || matchedVowel;
        i += matchedVowel.length;
        continue;
      }
    }

    // 2. Try matching consonant
    let matchedConsonant = "";
    let devConsonant = "";
    for (const [c, dev] of CONSONANTS) {
      if (word.startsWith(c, i)) {
        matchedConsonant = c;
        devConsonant = dev;
        break;
      }
    }

    if (matchedConsonant) {
      i += matchedConsonant.length;

      // Now check following vowel
      let matchedVowel = "";
      for (const v of ["aa", "ii", "ee", "uu", "oo", "ai", "au", "ou", "ri", "ru", "a", "i", "u", "e", "o"]) {
        if (word.startsWith(v, i)) {
          matchedVowel = v;
          break;
        }
      }

      if (matchedVowel) {
        // If matched 'a' and it's at the end of word (e.g. 'Sneha' or 'Gupta'), it's often 'aa' (ा)
        if (matchedVowel === "a" && (i + 1 === n || ["ha", "ta", "ma", "na", "ra", "sa", "ka", "la", "da", "ba", "ya"].includes(matchedConsonant + "a"))) {
          if (i + 1 === n && !["an", "am", "ar"].some(end => word.endsWith(end))) {
            result += devConsonant + "ा";
          } else {
            result += devConsonant + (VOWEL_MATRAS[matchedVowel] ?? "");
          }
        } else {
          result += devConsonant + (VOWEL_MATRAS[matchedVowel] ?? "");
        }
        i += matchedVowel.length;
      } else {
        // No following vowel -> check if at end of word or followed by another consonant
        if (i < n) {
          // If next is consonant, add virama/half consonant unless it already contains conjunct
          if (!devConsonant.includes("्")) {
            result += devConsonant + "्";
          } else {
            result += devConsonant;
          }
        } else {
          // At the end of word, standard Indian pronunciation does not require virama (e.g. Rakesh -> राकेश)
          result += devConsonant;
        }
      }
      continue;
    }

    // 3. Fallback independent vowel in middle of word (like in 'Rahul' -> 'ह' + 'उ' + 'ल')
    let midVowel = "";
    for (const v of ["aa", "ii", "ee", "uu", "oo", "ai", "au", "ou", "ri", "ru", "a", "i", "u", "e", "o"]) {
      if (word.startsWith(v, i)) {
        midVowel = v;
        break;
      }
    }
    if (midVowel) {
      result += INDEPENDENT_VOWELS[midVowel] || midVowel;
      i += midVowel.length;
      continue;
    }

    // Single character skip
    result += word[i];
    i++;
  }

  // Clean up any double halants/viramas
  return result.replace(/्+/g, "्");
}

export function transliterateText(text: string): string {
  if (!text) return text;
  // If text already has Devanagari, preserve it
  if (/[\u0900-\u097F]/.test(text)) return text;
  // Don't transliterate emails, URLs, or phone numbers
  if (text.includes("@") || text.includes("http") || /^[\d+\-\s(),.]+$/.test(text)) {
    return text;
  }

  // Transliterate words preserving delimiters (spaces, punctuation)
  return text.replace(/[a-zA-Z]+/g, (match) => {
    return transliterateWordToDevanagari(match);
  });
}
