import type { MetadataRoute } from "next";

const SITE_URL = "https://daisy.6x7.gr";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: { userAgent: "*", allow: "/", disallow: ["/waitlist"] },
    sitemap: `${SITE_URL}/sitemap.xml`,
  };
}
