from pathlib import Path

from bs4 import BeautifulSoup

from app.scraping.fetcher import HtmlFetcher

if __name__ == "__main__":
    url = "https://www.bbva.com.co/"
    fetcher = HtmlFetcher()
    result = fetcher.fetch(url)

    output_dir = Path("/tmp/scraping_debug")
    output_dir.mkdir(parents=True, exist_ok=True)
    html_file = output_dir / "bbva_homepage_raw.html"
    html_file.write_text(result.html, encoding="utf-8")

    soup = BeautifulSoup(result.html, "lxml")
    title = soup.title.get_text(strip=True) if soup.title else ""
    h1_tags = [
        h.get_text(strip=True) for h in soup.find_all("h1") if h.get_text(strip=True)
    ]
    links = [a.get("href") for a in soup.find_all("a", href=True)]

    print("Status:", result.status_code)
    print("Final URL:", result.final_url)
    print("Content-Type:", result.content_type)
    print("Saved HTML:", html_file)
    print("HTML Length:", len(result.html))
    print("Title:", title)
    print("H1 count:", len(h1_tags))
    print("First H1:", h1_tags[0] if h1_tags else "")
    print("Link count:", len(links))
    print("First 10 links:")
    for href in links[:10]:
        print(" -", href)
