from flask import Flask, jsonify
from scholarly import scholarly
from urllib.parse import urlparse, parse_qs

app = Flask(__name__)

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
        scholarly.fill(author, sections=['publications'])
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
            if get_pub_id(pub) == pub_id:
                scholarly.fill(pub)  # Fill with additional details
                return jsonify(pub)
        return jsonify({'error': 'Publication not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port = 21114)