# Numerical-domain policy

Every stage declares a semantic pixel domain and every frame declares its
minimum, maximum, bit depth and normalization state. These declarations are
validated at stage boundaries and are part of intermediate-export metadata.

The reference rules are:

1. Promote integer inputs to a signed wide type before subtraction,
   multiplication, convolution or accumulation. Unsigned wraparound is never a
   permitted implementation detail.
2. Preserve linear sensor precision through RAW-domain operations. Quantization
   occurs only at an explicitly documented stage boundary.
3. State rounding and saturation independently. `NumericPolicy` supports
   nearest-even, half-up and truncation followed by optional saturation.
4. Never infer a Bayer pattern, output range or transfer function from array
   dtype alone.
5. A bypassed stage must be numerically identical to absence of that stage.
6. Accelerated backends must compare against the NumPy reference using the
   per-stage tolerance and range declared by the relevant checklist evidence.

The historical algorithms retain some 8-bit conversions for compatibility.
Those conversions are contained by adapters and will be replaced only with
explicit regression evidence under checklist items 105, 127 and 128.
