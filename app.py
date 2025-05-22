from flask import Flask, jsonify
from scholarly import scholarly
from urllib.parse import urlparse, parse_qs
import redis
import json
from copy import deepcopy as dp


app = Flask(__name__)

# Redis functions
def init_redis():
    """Initialize and configure Redis client"""
    client = redis.Redis(host='127.0.0.1', port=11001, db=0)
    # Configure Redis to use LRU eviction policy with a max of 50 entries
    client.config_set('maxmemory-policy', 'allkeys-lru')
    client.config_set('maxmemory', '50mb')  # Set a reasonable memory limit
    return client

def get_from_cache(key):
    """Get data from Redis cache"""
    data = redis_client.get(key)
    if data:
        return json.loads(data)
    return None

def save_to_cache(key, data):
    """Save data to Redis cache"""
    redis_client.set(key, json.dumps(data), ex=604800)

# Initialize Redis
redis_client = init_redis()

# this flask app is used to serve the data from the scholarly library


def get_publication_id(publication):
    try:
        return publication["author_pub_id"]
    except:
        pass
    return None

def get_pub_id(pub):
    """Extract publication ID from publication URL"""
    url = pub.get('pub_url', '')
    if url:
        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query)
        citation_for_view = query_params.get('citation_for_view', [None])[0]
        if citation_for_view:
            _, cid = citation_for_view.split(':')
            return cid
    return None

@app.route('/author/<author_id>', methods=['GET'])
def get_author(author_id):
    """Get all author data including publications"""
    try:
        # Check if author data exists in Redis cache
        cache_key_publication_coauthor_filled = f"author:{author_id}:publication_coauthor"
        cache_key_publication_filled = f"author:{author_id}:publication"
        cached_data = get_from_cache(cache_key_publication_coauthor_filled)
        if cached_data:
            author = cached_data
            print("Author data found in cache")
        else:
            # If not in cache, fetch from scholarly
            author = scholarly.search_author_id(author_id)
            author_dp = dp(author)
            scholarly.fill(author, sections=['publications', 'coauthors'])
            scholarly.fill(author_dp, sections=['publications'])
            save_to_cache(cache_key_publication_coauthor_filled, author)
            save_to_cache(cache_key_publication_filled, author_dp)
        
        
        # Process coauthors to extract their IDs
        if 'coauthors' in author:
            for coauthor_id in range(len(author['coauthors'])):
                coauthor = author['coauthors'][coauthor_id]
                if 'scholar_id' not in coauthor and 'url_picture' in coauthor:
                    # Extract scholar_id from URL if available
                    try:
                        url = coauthor['url_picture']
                        parsed_url = urlparse(url)
                        query_params = parse_qs(parsed_url.query)
                        scholar_id = query_params.get('user', [None])[0]
                        if scholar_id:
                            coauthor['scholar_id'] = scholar_id
                    except:
                        pass
                author['coauthors'][coauthor_id] = coauthor['scholar_id']
        
                        
        return jsonify(author)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/author/<author_id>/publication/<pub_id>', methods=['GET'])
def get_publication(author_id, pub_id):
    """Get detailed publication data for a specific publication"""
    try:
        cache_key_publication = f"publication:{pub_id}"
        # Check if publication data exists in Redis cache
        cached_data = get_from_cache(cache_key_publication)
        if cached_data:
            return jsonify(cached_data)



        # Check if author data exists in Redis cache
        cache_key_publication_filled = f"author:{author_id}:publication"
        cached_data = get_from_cache(cache_key_publication_filled)
        if cached_data:
            author = jsonify(cached_data)
            print("Aauthor data found in cache")
        else:
            # If not in cache, fetch from scholarly
            author = scholarly.search_author_id(author_id)
            scholarly.fill(author, sections=['publications'])
            save_to_cache(cache_key_publication_filled, author)

        for pub in author['publications']:
            if str(get_publication_id(pub)) == str(pub_id):
                scholarly.fill(pub)
                save_to_cache(cache_key_publication, pub)


                return jsonify(pub)
        return jsonify({'error': 'Publication not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port = 21113)