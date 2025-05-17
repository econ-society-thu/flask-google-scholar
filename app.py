from flask import Flask, jsonify
from scholarly import scholarly
from urllib.parse import urlparse, parse_qs

app = Flask(__name__)

# this flask app is used to serve the data from the scholarly library


def get_publication_id(publication):
    try:
        return publication["author_pub_id"]
    except:
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
        author = scholarly.search_author_id(author_id)
        scholarly.fill(author, sections=['publications', 'coauthors'])
        
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
        author = scholarly.search_author_id(author_id)
        scholarly.fill(author, sections=['publications'])
        for pub in author['publications']:
            if str(get_publication_id(pub)) == str(pub_id):
                scholarly.fill(pub)  # Fill with additional details
                return jsonify(pub)
        return jsonify({'error': 'Publication not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='127.0.0.1', port = 21113)