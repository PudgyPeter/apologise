import { createClient } from '@supabase/supabase-js';

// Supabase configuration
const supabaseUrl = process.env.REACT_APP_SUPABASE_URL;
const supabaseAnonKey = process.env.REACT_APP_SUPABASE_ANON_KEY;

// Validate environment variables
if (!supabaseUrl || !supabaseAnonKey) {
  console.error('Missing Supabase environment variables!');
  console.error('Please set REACT_APP_SUPABASE_URL and REACT_APP_SUPABASE_ANON_KEY');
}

// Create Supabase client
export const supabase = createClient(supabaseUrl, supabaseAnonKey, {
  auth: {
    persistSession: true,
    autoRefreshToken: true,
  },
  realtime: {
    params: {
      eventsPerSecond: 10
    }
  }
});

// Helper function to extract keywords (same as backend)
export const extractKeywords = (text, minWordLength = 3) => {
  const stopWords = new Set([
    'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
    'of', 'with', 'by', 'from', 'up', 'about', 'into', 'through', 'during',
    'before', 'after', 'above', 'below', 'between', 'under', 'again', 'further',
    'then', 'once', 'here', 'there', 'when', 'where', 'why', 'how', 'all', 'both',
    'each', 'few', 'more', 'most', 'other', 'some', 'such', 'no', 'nor', 'not',
    'only', 'own', 'same', 'so', 'than', 'too', 'very', 'can', 'will', 'just',
    'should', 'now', 'was', 'were', 'been', 'being', 'have', 'has', 'had',
    'do', 'does', 'did', 'doing', 'would', 'could', 'ought', 'i', 'you', 'he',
    'she', 'it', 'we', 'they', 'them', 'their', 'what', 'which', 'who', 'whom',
    'this', 'that', 'these', 'those', 'am', 'is', 'are', 'be', 'as', 'if', 'my',
    'your', 'his', 'her', 'its', 'our', 'me', 'him', 'us', 'myself', 'yourself',
    'himself', 'herself', 'itself', 'ourselves', 'themselves'
  ]);

  // Clean and split text
  const words = text.toLowerCase().match(/\b[a-z]+\b/g) || [];

  // Filter out stop words and short words
  const keywords = words.filter(w => !stopWords.has(w) && w.length >= minWordLength);

  // Count frequencies
  const wordFreq = {};
  keywords.forEach(word => {
    wordFreq[word] = (wordFreq[word] || 0) + 1;
  });

  return wordFreq;
};

// Dream API functions using Supabase
export const dreamAPI = {
  // Get all dreams with optional filtering
  async getAll(filters = {}) {
    try {
      let query = supabase
        .from('dreams')
        .select('*')
        .order('date', { ascending: false });

      // Apply search filter
      if (filters.search) {
        query = query.or(`title.ilike.%${filters.search}%,content.ilike.%${filters.search}%`);
      }

      // Apply date range filters
      if (filters.startDate) {
        query = query.gte('date', filters.startDate);
      }
      if (filters.endDate) {
        query = query.lte('date', filters.endDate);
      }

      const { data, error } = await query;

      if (error) throw error;
      return data || [];
    } catch (error) {
      console.error('Error fetching dreams:', error);
      throw error;
    }
  },

  // Create a new dream
  async create(dreamData) {
    try {
      const keywords = extractKeywords(dreamData.content);

      const { data, error } = await supabase
        .from('dreams')
        .insert([{
          title: dreamData.title,
          content: dreamData.content,
          date: dreamData.date,
          tags: dreamData.tags || [],
          keywords: keywords
        }])
        .select()
        .single();

      if (error) throw error;
      return data;
    } catch (error) {
      console.error('Error creating dream:', error);
      throw error;
    }
  },

  // Update an existing dream
  async update(id, dreamData) {
    try {
      const keywords = extractKeywords(dreamData.content);

      const { data, error } = await supabase
        .from('dreams')
        .update({
          title: dreamData.title,
          content: dreamData.content,
          date: dreamData.date,
          tags: dreamData.tags || [],
          keywords: keywords
        })
        .eq('id', id)
        .select()
        .single();

      if (error) throw error;
      return data;
    } catch (error) {
      console.error('Error updating dream:', error);
      throw error;
    }
  },

  // Delete a dream
  async delete(id) {
    try {
      const { error } = await supabase
        .from('dreams')
        .delete()
        .eq('id', id);

      if (error) throw error;
      return { success: true };
    } catch (error) {
      console.error('Error deleting dream:', error);
      throw error;
    }
  },

  // Get statistics
  async getStats() {
    try {
      const { data: dreams, error } = await supabase
        .from('dreams')
        .select('content, keywords, date');

      if (error) throw error;

      if (!dreams || dreams.length === 0) {
        return {
          total_dreams: 0,
          total_words: 0,
          avg_words_per_dream: 0,
          top_keywords: [],
          dreams_by_month: {}
        };
      }

      let totalWords = 0;
      const allKeywords = {};
      const dreamsByMonth = {};

      dreams.forEach(dream => {
        // Count words
        const words = dream.content.split(/\s+/).length;
        totalWords += words;

        // Aggregate keywords
        if (dream.keywords) {
          Object.entries(dream.keywords).forEach(([word, count]) => {
            allKeywords[word] = (allKeywords[word] || 0) + count;
          });
        }

        // Group by month
        if (dream.date) {
          const monthKey = dream.date.substring(0, 7); // YYYY-MM
          dreamsByMonth[monthKey] = (dreamsByMonth[monthKey] || 0) + 1;
        }
      });

      // Sort keywords by frequency
      const topKeywords = Object.entries(allKeywords)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 50)
        .map(([word, count]) => ({ word, count }));

      return {
        total_dreams: dreams.length,
        total_words: totalWords,
        avg_words_per_dream: Math.round(totalWords / dreams.length * 10) / 10,
        top_keywords: topKeywords,
        dreams_by_month: dreamsByMonth
      };
    } catch (error) {
      console.error('Error getting stats:', error);
      throw error;
    }
  },

  // Subscribe to real-time changes
  subscribeToChanges(callback) {
    const subscription = supabase
      .channel('dreams_changes')
      .on('postgres_changes', 
        { event: '*', schema: 'public', table: 'dreams' },
        (payload) => {
          console.log('Real-time update:', payload);
          callback(payload);
        }
      )
      .subscribe();

    return subscription;
  },

  // Unsubscribe from real-time changes
  unsubscribe(subscription) {
    if (subscription) {
      supabase.removeChannel(subscription);
    }
  }
};

export default supabase;
