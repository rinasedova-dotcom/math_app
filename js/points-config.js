const POINTS_CONFIG = {
  pointsPerEuro: 10,
  actions: {
    football_goal: { label: "Football Goal", points: 4, icon: "football" },
    room_cleaning: { label: "Room Cleaning", points: 4, icon: "broom" },
    trash_handling: { label: "Trash Handling", points: 4, icon: "trash" },
    cooking: { label: "Cooking", points: 4, icon: "chef" },
    greek: { label: "Greek", comingSoon: true, icon: "book" },
    russian: { label: "Russian", comingSoon: true, icon: "book" },
    reading: { label: "Reading", pointsPerHour: 6, icon: "read" },
    babysitting: { label: "Babysitting", pointsPerHour: 3, icon: "babysitting" },
    custom: { label: "Custom", custom: true, icon: "custom" },
  },
};

function computeHourlyPoints(actionType, minutes) {
  const rate = POINTS_CONFIG.actions[actionType].pointsPerHour;
  return Math.floor((minutes * rate) / 60);
}

function pointsToEuro(points) {
  return points / POINTS_CONFIG.pointsPerEuro;
}

function todaysSecretCode() {
  const now = new Date();
  const dd = String(now.getDate()).padStart(2, "0");
  const mm = String(now.getMonth() + 1).padStart(2, "0");
  const yy = String(now.getFullYear()).slice(-2);
  return dd + mm + yy;
}
