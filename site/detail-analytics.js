/* Detail-page visits use Umami's automatic pageview; clicks share catalog event names. */
(() => {
  "use strict";
  const page = document.querySelector(".detail-page");
  if (!page) return;
  const trackClick = (event) => {
    if (event.type === "auxclick" && event.button !== 1) return;
    const link = event.target?.closest?.("a[href]");
    if (!link || !page.contains(link)) return;
    let destination;
    try { destination = new URL(link.getAttribute("href"), window.location.href); }
    catch { return; }
    if (!["http:", "https:"].includes(destination.protocol)) return;
    if ([window.location.hostname, "openknowledgegraphs.com", "www.openknowledgegraphs.com"].includes(destination.hostname)) return;
    if (typeof window.umami?.track !== "function") return;
    try {
      window.umami.track("outbound_link_click", {
        tab: page.dataset.catalogTab,
        resourceTitle: page.dataset.resourceTitle.slice(0, 120),
        linkType: link.dataset.linkType || "external",
        destinationHost: destination.hostname,
        sourcePage: "detail",
        resourcePath: window.location.pathname,
      });
    } catch { /* Analytics must never block normal navigation. */ }
  };
  document.addEventListener("click", trackClick);
  document.addEventListener("auxclick", trackClick);
})();
