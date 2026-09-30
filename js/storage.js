const PREFS_KEY = "mathQuizPrefs";

const supabaseClient = window.supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

function rowToResult(row) {
  return {
    id: row.id,
    timestamp: row.created_at,
    courseId: row.course_id,
    courseName: row.course_name,
    questionNumber: row.question_number,
    questionText: row.question_text,
    answerGiven: row.answer_given,
    correctAnswer: row.correct_answer,
    isCorrect: row.is_correct,
  };
}

async function getResults() {
  const { data, error } = await supabaseClient
    .from("results")
    .select("*")
    .order("created_at", { ascending: true });
  if (error) {
    console.error("Failed to load results from Supabase", error);
    return [];
  }
  return data.map(rowToResult);
}

async function saveResult(result) {
  const row = {
    course_id: result.courseId,
    course_name: result.courseName,
    question_number: result.questionNumber,
    question_text: result.questionText,
    answer_given: result.answerGiven,
    correct_answer: result.correctAnswer,
    is_correct: result.isCorrect,
  };
  const { data, error } = await supabaseClient
    .from("results")
    .insert(row)
    .select()
    .single();
  if (error) {
    console.error("Failed to save result to Supabase", error);
    return null;
  }
  return rowToResult(data);
}

function rowToAction(row) {
  return {
    id: row.id,
    timestamp: row.created_at,
    actionType: row.action_type,
    points: row.points,
    detail: row.detail,
  };
}

async function getPointsActions() {
  const { data, error } = await supabaseClient
    .from("points_actions")
    .select("*")
    .order("created_at", { ascending: true });
  if (error) {
    console.error("Failed to load point actions from Supabase", error);
    return [];
  }
  return data.map(rowToAction);
}

async function savePointsAction(actionType, points, detail) {
  const row = { action_type: actionType, points: points, detail: detail || null };
  const { data, error } = await supabaseClient
    .from("points_actions")
    .insert(row)
    .select()
    .single();
  if (error) {
    console.error("Failed to save point action to Supabase", error);
    return null;
  }
  return rowToAction(data);
}

function rowToRedemption(row) {
  return {
    id: row.id,
    timestamp: row.created_at,
    pointsRedeemed: row.points_redeemed,
    euroValue: row.euro_value,
  };
}

async function getPointsRedemptions() {
  const { data, error } = await supabaseClient
    .from("points_redemptions")
    .select("*")
    .order("created_at", { ascending: true });
  if (error) {
    console.error("Failed to load redemptions from Supabase", error);
    return [];
  }
  return data.map(rowToRedemption);
}

async function savePointsRedemption(pointsRedeemed, euroValue) {
  const row = { points_redeemed: pointsRedeemed, euro_value: euroValue };
  const { data, error } = await supabaseClient
    .from("points_redemptions")
    .insert(row)
    .select()
    .single();
  if (error) {
    console.error("Failed to save redemption to Supabase", error);
    return null;
  }
  return rowToRedemption(data);
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
