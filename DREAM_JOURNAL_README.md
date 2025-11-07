# Dream Journal System

A comprehensive dream logging system with keyword analysis and statistics tracking.

## Features

### 📝 Dream Logging
- **Manual Entry**: Log your dreams with title, date, content, and custom tags
- **Edit & Delete**: Modify or remove dream entries at any time
- **Rich Text Support**: Write detailed dream descriptions

### 🔍 Keyword Analysis
- **Automatic Extraction**: Keywords are automatically extracted from dream content
- **Smart Filtering**: Excludes common filler words (a, the, and, etc.)
- **Frequency Tracking**: See how often specific words appear across all dreams
- **Highlighted Keywords**: Top keywords are highlighted when viewing dream details

### 📊 Statistics Dashboard
- **Total Dreams**: Track how many dreams you've logged
- **Word Count**: See total words written and average per dream
- **Top Keywords**: View the most frequently used words across all dreams
- **Monthly Breakdown**: See how many dreams you logged each month

### 🔎 Search & Filter
- **Full-Text Search**: Search through dream titles, content, and tags
- **Tag System**: Organize dreams with custom tags (e.g., "nightmare", "flying", "family")
- **Date Filtering**: Built-in support for filtering by date range

### 🎨 User Interface
- **Dark Mode**: Toggle between light and dark themes
- **Responsive Design**: Works on desktop, tablet, and mobile
- **Expandable Cards**: Click on dreams to see full content and keyword analysis
- **Keyword Cloud**: Visual representation of keywords with size based on frequency

## How to Use

### Accessing the Dream Journal
Navigate to `/dreams` in your browser (e.g., `http://localhost:5000/dreams`)

### Adding a New Dream
1. Click the **"New Dream"** button
2. Fill in the form:
   - **Title**: Give your dream a memorable title
   - **Date**: When you had the dream (defaults to today)
   - **Dream Content**: Describe your dream in detail
   - **Tags**: Add comma-separated tags (optional)
3. Click **"Save Dream"**

### Viewing Dreams
- Dreams are displayed in reverse chronological order (newest first)
- Click on any dream card to expand and see:
  - Full dream content
  - Highlighted keywords
  - Keyword frequency for that specific dream

### Editing Dreams
1. Click the **Edit** icon (pencil) on any dream card
2. Modify the fields as needed
3. Click **"Update Dream"**

### Deleting Dreams
1. Click the **Delete** icon (trash) on any dream card
2. Confirm the deletion

### Searching Dreams
- Use the search bar at the top to filter dreams
- Search works across titles, content, and tags

## Technical Details

### Backend API Endpoints

#### Get All Dreams
```
GET /api/dreams
Query Parameters:
  - search: Filter by search term
  - start_date: Filter dreams from this date
  - end_date: Filter dreams until this date
```

#### Create Dream
```
POST /api/dreams
Body: {
  "title": "Dream title",
  "content": "Dream description",
  "date": "YYYY-MM-DD",
  "tags": ["tag1", "tag2"]
}
```

#### Update Dream
```
PUT /api/dreams/{dream_id}
Body: {
  "title": "Updated title",
  "content": "Updated content",
  "date": "YYYY-MM-DD",
  "tags": ["tag1", "tag2"]
}
```

#### Delete Dream
```
DELETE /api/dreams/{dream_id}
```

#### Get Statistics
```
GET /api/dreams/stats
Returns:
  - total_dreams
  - total_words
  - avg_words_per_dream
  - top_keywords (array of {word, count})
  - dreams_by_month (object)
```

### Data Storage
Dreams are stored in `data/dreams.json` with the following structure:
```json
{
  "id": 1,
  "title": "Flying Dream",
  "content": "I was flying over the city...",
  "date": "2024-11-07",
  "tags": ["flying", "city"],
  "keywords": {
    "flying": 3,
    "city": 2,
    "sky": 1
  },
  "created_at": "2024-11-07T14:30:00",
  "updated_at": "2024-11-07T14:35:00"
}
```

### Keyword Extraction
The system uses a comprehensive stop-words list to filter out common words like:
- Articles: a, an, the
- Conjunctions: and, or, but
- Pronouns: I, you, he, she, it
- Common verbs: is, are, was, were, have, has
- And many more...

Only words with 3+ characters that aren't in the stop-words list are counted as keywords.

## Tips for Best Results

1. **Be Descriptive**: The more detail you provide, the better the keyword analysis
2. **Use Tags**: Categorize dreams with tags for easier organization
3. **Log Regularly**: Try to log dreams as soon as you wake up for best recall
4. **Review Patterns**: Use the statistics to identify recurring themes in your dreams
5. **Search Often**: Use the search feature to find dreams with specific themes or elements

## Dark Mode
Toggle dark mode using the sun/moon icon in the top-right corner. Your preference is saved automatically.

## Responsive Design
The Dream Journal works on all screen sizes:
- **Desktop**: Full sidebar with keywords and monthly stats
- **Tablet**: Sidebar hidden, focus on dream content
- **Mobile**: Optimized layout with stacked stats cards
