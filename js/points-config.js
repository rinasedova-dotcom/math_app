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
  },
};

function computeReadingPoints(minutes) {
  return Math.floor((minutes * POINTS_CONFIG.actions.reading.pointsPerHour) / 60);
}

function pointsToEuro(points) {
  return points / POINTS_CONFIG.pointsPerEuro;
}
