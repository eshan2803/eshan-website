const express = require('express');
const cors = require('cors');
const fs = require('fs');
const path = require('path');

const app = express();
const PORT = 3000;

// Middleware
app.use(cors());
app.use(express.json());

// Leaderboard file path
const LEADERBOARD_FILE = path.join(__dirname, 'leaderboard.json');

// Initialize leaderboard file if it doesn't exist
if (!fs.existsSync(LEADERBOARD_FILE)) {
    fs.writeFileSync(LEADERBOARD_FILE, JSON.stringify([]));
}

// Helper function to read leaderboard
function readLeaderboard() {
    try {
        const data = fs.readFileSync(LEADERBOARD_FILE, 'utf8');
        return JSON.parse(data);
    } catch (error) {
        console.error('Error reading leaderboard:', error);
        return [];
    }
}

// Helper function to write leaderboard
function writeLeaderboard(data) {
    try {
        fs.writeFileSync(LEADERBOARD_FILE, JSON.stringify(data, null, 2));
        return true;
    } catch (error) {
        console.error('Error writing leaderboard:', error);
        return false;
    }
}

// GET /api/leaderboard - Get top 10 scores
app.get('/api/leaderboard', (req, res) => {
    const leaderboard = readLeaderboard();
    // Sort by total cost (ascending) and return top 10
    const top10 = leaderboard
        .sort((a, b) => a.totalCost - b.totalCost)
        .slice(0, 10);

    res.json({
        success: true,
        leaderboard: top10
    });
});

// POST /api/leaderboard - Submit a new score
app.post('/api/leaderboard', (req, res) => {
    const { username, totalCost, emergencyAlerts, blackouts, season } = req.body;

    // Validation
    if (!username || typeof totalCost !== 'number' ||
        typeof emergencyAlerts !== 'number' || typeof blackouts !== 'number') {
        return res.status(400).json({
            success: false,
            error: 'Invalid data. Required: username, totalCost, emergencyAlerts, blackouts'
        });
    }

    // Only accept perfect games (0 alerts, 0 blackouts)
    if (emergencyAlerts !== 0 || blackouts !== 0) {
        return res.status(400).json({
            success: false,
            error: 'Only perfect games (0 alerts, 0 blackouts) can be submitted'
        });
    }

    // Read current leaderboard
    let leaderboard = readLeaderboard();

    // Create new entry
    const newEntry = {
        username: username.trim().substring(0, 20), // Limit username length
        totalCost: Math.round(totalCost),
        emergencyAlerts: 0,
        blackouts: 0,
        season: season || 'unknown',
        timestamp: new Date().toISOString()
    };

    // Add new entry
    leaderboard.push(newEntry);

    // Sort by total cost and keep only top 10
    leaderboard = leaderboard
        .sort((a, b) => a.totalCost - b.totalCost)
        .slice(0, 10);

    // Save to file
    if (writeLeaderboard(leaderboard)) {
        // Find rank of new entry
        const rank = leaderboard.findIndex(entry =>
            entry.username === newEntry.username &&
            entry.timestamp === newEntry.timestamp
        ) + 1;

        res.json({
            success: true,
            message: rank > 0 ? `Congratulations! You ranked #${rank}` : 'Good try! Keep improving.',
            rank: rank > 0 ? rank : null,
            entry: newEntry
        });
    } else {
        res.status(500).json({
            success: false,
            error: 'Failed to save leaderboard'
        });
    }
});

// Start server
app.listen(PORT, () => {
    console.log(`🚀 Leaderboard server running on http://localhost:${PORT}`);
    console.log(`📊 Leaderboard API: http://localhost:${PORT}/api/leaderboard`);
});
