export const validateSite = (site: string): boolean => {
  return site.length >= 2;
};

export const validateEmail = (email: string): boolean => {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email);
};

export const validateFieldPair = (
  site: string,
  email: string
): { isValid: boolean; errors: Record<string, string> } => {
  const errors: Record<string, string> = {};

  if (!site) {
    errors.site = "Le site est requis";
  } else if (!validateSite(site)) {
    errors.site = "Le site doit contenir au moins 2 caractères";
  }

  if (!email) {
    errors.email_address = "L'email est requis";
  } else if (!validateEmail(email)) {
    errors.email_address = "Format d'email invalide";
  }

  return {
    isValid: Object.keys(errors).length === 0,
    errors,
  };
};
