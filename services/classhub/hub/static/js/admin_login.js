(function () {
  const form = document.getElementById("login-form");
  if (!form) return;

  const username = form.querySelector('input[name="username"]');
  const password = form.querySelector('input[name="password"]');
  const otpToken = form.querySelector('input[name="otp_token"]');

  if (username) {
    username.setAttribute("autocomplete", "off");
    username.setAttribute("autocapitalize", "none");
    username.setAttribute("spellcheck", "false");
  }
  if (password) {
    password.setAttribute("autocomplete", "new-password");
  }
  if (otpToken) {
    otpToken.setAttribute("autocomplete", "one-time-code");
    otpToken.setAttribute("inputmode", "numeric");
  }
})();
