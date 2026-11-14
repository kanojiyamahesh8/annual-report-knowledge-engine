"use strict";

const form = document.querySelector("#ask-form");
const input = document.querySelector("#question");
const button = form.querySelector("button");
const result = document.querySelector("#result");
const answer = document.querySelector("#answer");
const excerpts = document.querySelector("#excerpts");
const error = document.querySelector("#error");

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const question = input.value.trim();
  if (!question) {
    error.textContent = "Enter a question to search the report.";
    error.hidden = false;
    return;
  }

  error.hidden = true;
  result.hidden = true;
  button.disabled = true;
  button.textContent = "Searching…";
  try {
    const response = await fetch("/api/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || "The report could not be searched.");
    answer.textContent = payload.answer;
    excerpts.replaceChildren();
    for (const excerpt of payload.excerpts || []) {
      const block = document.createElement("blockquote");
      const text = document.createElement("p");
      text.textContent = excerpt.text;
      const citation = document.createElement("cite");
      citation.textContent = `PDF page${excerpt.pages.length === 1 ? "" : "s"} ${excerpt.pages.join(", ")}`;
      block.append(text, citation);
      excerpts.appendChild(block);
    }
    result.hidden = false;
  } catch (requestError) {
    error.textContent = requestError.message;
    error.hidden = false;
  } finally {
    button.disabled = false;
    button.textContent = "Ask report";
  }
});
