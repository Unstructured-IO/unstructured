document.addEventListener("DOMContentLoaded", function () {
  const githubStarsComponents = document.getElementsByClassName("github-stars"),
    url = "https://api.github.com/repos/unstructured-io/unstructured";

  const createNode = (element) => {
    return document.createElement(element);
  };
  const append = (parent, el) => {
    return parent.appendChild(el);
  };

  fetch(url)
    .then((response) => {
      return response.json();
    })
    .then((data) => {
      let leftLink = createNode("a");
      let rightLink = createNode("a");
      leftLink.classList.add("--left");
      rightLink.classList.add("--right");
      leftLink.target = "_blank";
      leftLink.href = `${data.html_url}`;
      leftLink.innerHTML = `<svg width="19" height="19" viewBox="0 0 19 19" fill="none" xmlns="http://www.w3.org/2000/svg">
<path d="M8.43359 0.0678272C4.05472 0.5578 0.532587 4.1836 0.0566223 8.59336C-0.419342 13.1991 2.15086 17.3149 6.05377 18.8828C6.33935 18.9808 6.62493 18.7848 6.62493 18.3928V16.8249C6.62493 16.8249 6.24416 16.9229 5.76819 16.9229C4.43549 16.9229 3.86434 15.747 3.76914 15.061C3.67395 14.669 3.48357 14.375 3.19799 14.081C2.91241 13.9831 2.81721 13.9831 2.81721 13.8851C2.81721 13.6891 3.10279 13.6891 3.19799 13.6891C3.76914 13.6891 4.24511 14.375 4.43549 14.669C4.91146 15.453 5.48261 15.649 5.76819 15.649C6.14896 15.649 6.43454 15.551 6.62493 15.453C6.72012 14.767 7.0057 14.081 7.57686 13.6891C5.38742 13.1991 3.76914 11.9252 3.76914 9.76929C3.76914 8.69135 4.24511 7.61341 4.91146 6.82945C4.81626 6.63346 4.72107 6.14349 4.72107 5.45753C4.72107 5.06555 4.72107 4.47758 5.00665 3.88962C5.00665 3.88962 6.33935 3.88962 7.67205 5.16355C8.14802 4.96756 8.81437 4.86956 9.48071 4.86956C10.1471 4.86956 10.8134 4.96756 11.3846 5.16355C12.6221 3.88962 14.05 3.88962 14.05 3.88962C14.2404 4.47758 14.2404 5.06555 14.2404 5.45753C14.2404 6.24149 14.1452 6.63346 14.05 6.82945C14.7163 7.61341 15.1923 8.59335 15.1923 9.76929C15.1923 11.9252 13.574 13.1991 11.3846 13.6891C11.9557 14.179 12.3365 15.061 12.3365 15.9429V18.4908C12.3365 18.7848 12.6221 19.0788 13.0029 18.9808C16.525 17.5109 19 13.9831 19 9.86728C19 3.98761 14.1452 -0.618135 8.43359 0.0678272Z" fill="white"/>
</svg> Star`;
      rightLink.target = "_blank";
      rightLink.href = `${data.html_url}/stargazers`;
      rightLink.innerHTML = data.stargazers_count.toLocaleString('en-US');
      Array.from(githubStarsComponents).forEach((component, index) => {
        append(component, leftLink.cloneNode(true));
        append(component, rightLink.cloneNode(true));
      });
    })
    .catch((error) => {
      console.log(error);
    });
});
