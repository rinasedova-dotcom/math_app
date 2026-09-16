async function loadCourseManifest() {
  const res = await fetch("data/courses.json");
  if (!res.ok) throw new Error("Could not load course list");
  const manifest = await res.json();
  return manifest.courses;
}

async function loadCourseData(course) {
  const res = await fetch(course.dataFile);
  if (!res.ok) throw new Error("Could not load " + course.dataFile);
  return res.json();
}

async function loadAllCourses() {
  const manifest = await loadCourseManifest();
  const full = await Promise.all(
    manifest.map(async (c) => {
      const data = await loadCourseData(c);
      return {
        id: data.id,
        name: data.name,
        source: data.source,
        imagePath: data.imagePath,
        questions: data.questions,
      };
    })
  );
  return full;
}

function buildQuestionPool(courses, selectedIds) {
  const pool = [];
  courses.forEach((course) => {
    if (!selectedIds.includes(course.id)) return;
    course.questions.forEach((q) => {
      pool.push({
        courseId: course.id,
        courseName: course.name,
        imagePath: course.imagePath,
        question: q,
      });
    });
  });
  return pool;
}
