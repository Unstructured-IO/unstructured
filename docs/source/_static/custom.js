document.addEventListener("DOMContentLoaded", function() {
    var script = document.createElement("script");
    script.src = "https://widget.kapa.ai/kapa-widget.bundle.js";
    script.setAttribute("data-website-id", "8ae12a97-484a-4704-8127-b6f17ebc6bcf");
    script.setAttribute("data-project-name", "Unstructured");
    script.setAttribute("data-project-color", "#0CDDF8");
    script.setAttribute("data-project-logo", "https://raw.githubusercontent.com/Unstructured-IO/unstructured/main/img/unstructured_logo.png");
    script.setAttribute("data-modal-example-questions", "Are OpenAI embeddings supported?,How can I partition a document?,How do I use the library with Docker?,Can I ingest data from Box?");
    script.async = true;
    document.head.appendChild(script);
});