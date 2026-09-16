const STORAGE_KEY = "mathQuizResults";
const PREFS_KEY = "mathQuizPrefs";

function getResults() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch (e) {
    return [];
  }
}

function saveResult(result) {
  const results = getResults();
  result.id = Date.now() + "-" + Math.random().toString(36).slice(2, 8);
  result.timestamp = new Date().toISOString();
  results.push(result);
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(results));
  } catch (e) {
    /* storage unavailable; ignore */
  }
  return result;
}

function clearResults() {
  try {
    localStorage.removeItem(STORAGE_KEY);
  } catch (e) {}
}

function getPrefs() {
  try {
    const raw = localStorage.getItem(PREFS_KEY);
    return raw ? JSON.parse(raw) : {};
  } catch (e) {
    return {};
  }
}

function savePrefs(prefs) {
  try {
    localStorage.setItem(PREFS_KEY, JSON.stringify(prefs));
  } catch (e) {}
}
